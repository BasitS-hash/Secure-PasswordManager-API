-- Add updated_at to password_entries with an auto-update trigger
ALTER TABLE password_entries ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS password_entries_updated_at ON password_entries;
CREATE TRIGGER password_entries_updated_at
  BEFORE UPDATE ON password_entries
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
