# 🌐 Website Added - Complete with UI!

Your Secure Password Manager API now includes a **beautiful, interactive website**!

## ✨ What's Included

### 🎨 Landing Page (`/`)
- Beautiful gradient hero section
- Feature showcase cards
- Responsive design for mobile/desktop
- Professional animations

### 🔐 Interactive Password Manager (`/#app`)
- **Register Account** - Create new user
- **Login** - Secure authentication
- **Password Vault** - Store encrypted passwords
- **Add Passwords** - With URL metadata
- **View/Copy Passwords** - Client-side decryption
- **Generate Secure Passwords** - Cryptographically random

### 📚 API Documentation (`/docs.html`)
- Complete endpoint reference
- Request/response examples
- cURL examples
- Security notes

## 🚀 How to Access

### Local Development
```bash
npm install
npm start
# Or with Docker
./deploy.sh
```

Visit: **http://localhost:4000**

### After GitHub Deploy
Your website will be live at:
- `http://your-server-ip`
- `https://api.yourdomain.com` (after SSL setup)

## 🎯 Pages

| URL | Description |
|-----|-------------|
| `/` | Landing page + web app |
| `/docs.html` | API documentation |
| `/api` | API health check (JSON) |
| `/api/auth/*` | Authentication endpoints |
| `/api/entries` | Password entries endpoints |

## 🔒 Security Features in Web App

✅ **Client-Side Encryption** - All passwords encrypted in browser before sending to server  
✅ **Zero-Knowledge** - Server never sees plaintext passwords  
✅ **Web Crypto API** - Native browser cryptography (AES-256-GCM)  
✅ **PBKDF2 Key Derivation** - 100,000 iterations for browser compatibility  
✅ **Secure Password Generator** - Cryptographically random passwords  
✅ **Session Storage** - Tokens stored in sessionStorage (not localStorage)  
✅ **Copy to Clipboard** - Quick password copying  

## 🎨 Design Features

- Modern gradient design (purple/blue theme)
- Smooth animations and transitions
- Responsive mobile-first layout
- Clean, professional typography
- Accessible form inputs
- Alert notifications
- Tab-based navigation

## 🔧 How It Works

1. **User registers** → Server stores Argon2 hash + generates encryption salt
2. **User logs in** → Receives JWT token + encryption salt
3. **Browser derives key** → PBKDF2(master password, salt) → AES-256 key
4. **Add password** → Encrypt in browser → Send ciphertext to server
5. **View password** → Fetch ciphertext → Decrypt in browser → Display
6. **Zero-knowledge** → Server only stores encrypted blobs

## 📱 Screenshots

When deployed, users will see:
- 🏠 Beautiful landing page explaining features
- 🔐 Secure login/register forms
- 💾 Password vault interface
- 🎲 Password generator
- 📋 Copy/view password actions

## 🚀 Deploy Now

```bash
# Add all files
git add .
git commit -m "Add beautiful website UI"
git push origin main

# GitHub Actions will deploy everything automatically!
```

## 🌐 Files Added

```
public/
├── index.html    # Main landing page + app (Beautiful UI)
├── app.js        # Client-side JavaScript (encryption, API calls)
└── docs.html     # API documentation page
```

## ✅ Ready to Go Live!

Your password manager now has:
- ✅ Professional landing page
- ✅ Working web application
- ✅ Client-side encryption
- ✅ API documentation
- ✅ Mobile responsive design
- ✅ Production-ready code

**Just push to GitHub and it goes live automatically!** 🎉

---

Visit `http://localhost:4000` to try it now, or deploy to see it live on your domain!
