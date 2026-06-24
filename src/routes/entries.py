import base64
import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from src import db
from src.logger import logger
from src.middleware.audit import audit_log
from src.middleware.auth import get_current_user

router = APIRouter(prefix="/entries", tags=["entries"])

# Upper bounds to prevent an authenticated user from storing oversized blobs
# (storage-amplification abuse). Encrypted secrets are small in practice.
MAX_NAME_LENGTH = 256
MAX_FIELD_BYTES = 8192  # ciphertext/iv/tag (base64) ceiling
MAX_META_BYTES = 4096

ENTRY_SELECT = """SELECT id, name, encode(ciphertext, 'base64') AS ciphertext,
                         encode(iv, 'base64') AS iv, encode(tag, 'base64') AS tag,
                         meta, created_at, updated_at
                  FROM password_entries"""


class EntryRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=MAX_NAME_LENGTH)
    ciphertext: Optional[str] = Field(default=None, max_length=MAX_FIELD_BYTES)
    iv: Optional[str] = Field(default=None, max_length=MAX_FIELD_BYTES)
    tag: Optional[str] = Field(default=None, max_length=MAX_FIELD_BYTES)
    meta: Optional[dict] = None

    @field_validator("meta")
    @classmethod
    def _meta_within_limit(cls, value):
        if value is not None and len(json.dumps(value)) > MAX_META_BYTES:
            raise ValueError(f"meta must not exceed {MAX_META_BYTES} bytes")
        return value

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "GitHub",
                "ciphertext": "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHg=",
                "iv": "eXl5eXl5eXl5eXl5",
                "tag": "enp6enp6enp6enp6enp6eg==",
                "meta": {"label": "work"},
            }
        }
    }


def decode_entry_fields(body: EntryRequest):
    """Strictly decode the base64 fields, rejecting malformed input with 400."""
    try:
        return (
            base64.b64decode(body.ciphertext, validate=True),
            base64.b64decode(body.iv, validate=True),
            base64.b64decode(body.tag, validate=True),
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 encoding")


@router.post("/", status_code=201)
def create_entry(
    body: EntryRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    user_id = user["sub"]
    ip = request.client.host if request.client else None

    if not all([body.name, body.ciphertext, body.iv, body.tag]):
        audit_log(
            user_id=user_id,
            action="create_entry",
            ip=ip,
            success=False,
            message="missing required fields",
        )
        raise HTTPException(
            status_code=400, detail="name, ciphertext, iv and tag are required"
        )

    try:
        ciphertext, iv, tag = decode_entry_fields(body)
        meta = json.dumps(body.meta) if body.meta is not None else None
        db.execute(
            "INSERT INTO password_entries(user_id, name, ciphertext, iv, tag, meta) VALUES(%s,%s,%s,%s,%s,%s)",
            (user_id, body.name, ciphertext, iv, tag, meta),
        )
        audit_log(user_id=user_id, action="create_entry", ip=ip, success=True)
        return {"ok": True}

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Create entry error: {err}")
        audit_log(
            user_id=user_id,
            action="create_entry",
            ip=ip,
            success=False,
            message="create entry error",
        )
        raise HTTPException(status_code=500, detail="Failed to create entry")


@router.get("/")
def list_entries(request: Request, user: dict = Depends(get_current_user)):
    user_id = user["sub"]
    ip = request.client.host if request.client else None

    try:
        result = db.query(
            ENTRY_SELECT + " WHERE user_id=%s ORDER BY created_at DESC",
            (user_id,),
        )
        audit_log(user_id=user_id, action="list_entries", ip=ip, success=True)
        return {"entries": result or []}

    except Exception as err:
        logger.error(f"List entries error: {err}")
        audit_log(
            user_id=user_id,
            action="list_entries",
            ip=ip,
            success=False,
            message="list entries error",
        )
        raise HTTPException(status_code=500, detail="Failed to list entries")


@router.get("/{entry_id}")
def get_entry(entry_id: UUID, request: Request, user: dict = Depends(get_current_user)):
    user_id = user["sub"]
    ip = request.client.host if request.client else None

    try:
        result = db.query(
            ENTRY_SELECT + " WHERE id=%s AND user_id=%s",
            (str(entry_id), user_id),
        )
        if not result:
            audit_log(
                user_id=user_id,
                action="get_entry",
                ip=ip,
                success=False,
                message="not found",
            )
            raise HTTPException(status_code=404, detail="Entry not found")

        audit_log(user_id=user_id, action="get_entry", ip=ip, success=True)
        return result[0]

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Get entry error: {err}")
        audit_log(
            user_id=user_id,
            action="get_entry",
            ip=ip,
            success=False,
            message="get entry error",
        )
        raise HTTPException(status_code=500, detail="Failed to get entry")


@router.put("/{entry_id}")
def update_entry(
    entry_id: UUID,
    body: EntryRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    user_id = user["sub"]
    ip = request.client.host if request.client else None
    entry_id = str(entry_id)

    if not all([body.name, body.ciphertext, body.iv, body.tag]):
        audit_log(
            user_id=user_id,
            action="update_entry",
            ip=ip,
            success=False,
            message="missing required fields",
        )
        raise HTTPException(
            status_code=400, detail="name, ciphertext, iv and tag are required"
        )

    try:
        if not db.query(
            "SELECT id FROM password_entries WHERE id=%s AND user_id=%s",
            (entry_id, user_id),
        ):
            audit_log(
                user_id=user_id,
                action="update_entry",
                ip=ip,
                success=False,
                message="not found",
            )
            raise HTTPException(status_code=404, detail="Entry not found")

        ciphertext, iv, tag = decode_entry_fields(body)
        meta = json.dumps(body.meta) if body.meta is not None else None
        db.execute(
            """UPDATE password_entries
               SET name=%s, ciphertext=%s, iv=%s, tag=%s, meta=%s, updated_at=now()
               WHERE id=%s AND user_id=%s""",
            (body.name, ciphertext, iv, tag, meta, entry_id, user_id),
        )
        audit_log(user_id=user_id, action="update_entry", ip=ip, success=True)
        return {"ok": True}

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Update entry error: {err}")
        audit_log(
            user_id=user_id,
            action="update_entry",
            ip=ip,
            success=False,
            message="update entry error",
        )
        raise HTTPException(status_code=500, detail="Failed to update entry")


@router.delete("/{entry_id}")
def delete_entry(
    entry_id: UUID, request: Request, user: dict = Depends(get_current_user)
):
    user_id = user["sub"]
    ip = request.client.host if request.client else None
    entry_id = str(entry_id)

    try:
        if not db.query(
            "SELECT id FROM password_entries WHERE id=%s AND user_id=%s",
            (entry_id, user_id),
        ):
            audit_log(
                user_id=user_id,
                action="delete_entry",
                ip=ip,
                success=False,
                message="not found",
            )
            raise HTTPException(status_code=404, detail="Entry not found")

        db.execute(
            "DELETE FROM password_entries WHERE id=%s AND user_id=%s",
            (entry_id, user_id),
        )
        audit_log(user_id=user_id, action="delete_entry", ip=ip, success=True)
        return {"ok": True}

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Delete entry error: {err}")
        audit_log(
            user_id=user_id,
            action="delete_entry",
            ip=ip,
            success=False,
            message="delete entry error",
        )
        raise HTTPException(status_code=500, detail="Failed to delete entry")
