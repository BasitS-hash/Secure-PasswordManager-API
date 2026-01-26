// API Configuration
const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:4000/api'
    : '/api'; // Uses same domain in production

// Global state
let currentUser = null;
let accessToken = null;
let refreshToken = null;
let encryptionSalt = null;
let encryptionKey = null;

// Utility Functions
function showAlert(message, type = 'success') {
    const container = document.getElementById('alert-container');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    container.innerHTML = '';
    container.appendChild(alert);
    setTimeout(() => alert.remove(), 5000);
}

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// Crypto Functions (using Web Crypto API)
async function deriveEncryptionKey(masterPassword, saltHex) {
    const encoder = new TextEncoder();
    const passwordBuffer = encoder.encode(masterPassword);
    const saltBuffer = hexToBuffer(saltHex);

    // Import password as key material
    const keyMaterial = await crypto.subtle.importKey(
        'raw',
        passwordBuffer,
        'PBKDF2',
        false,
        ['deriveBits', 'deriveKey']
    );

    // Derive 256-bit key using PBKDF2 (simulating Argon2 for browser compatibility)
    const key = await crypto.subtle.deriveKey(
        {
            name: 'PBKDF2',
            salt: saltBuffer,
            iterations: 100000,
            hash: 'SHA-256'
        },
        keyMaterial,
        { name: 'AES-GCM', length: 256 },
        true,
        ['encrypt', 'decrypt']
    );

    return key;
}

async function encryptPassword(plaintext, key) {
    const encoder = new TextEncoder();
    const data = encoder.encode(plaintext);
    const iv = crypto.getRandomValues(new Uint8Array(12));

    const ciphertext = await crypto.subtle.encrypt(
        { name: 'AES-GCM', iv: iv },
        key,
        data
    );

    return {
        ciphertext: bufferToBase64(ciphertext),
        iv: bufferToBase64(iv),
        tag: '' // Tag is included in ciphertext for AES-GCM in Web Crypto
    };
}

async function decryptPassword(ciphertextB64, ivB64, key) {
    const ciphertext = base64ToBuffer(ciphertextB64);
    const iv = base64ToBuffer(ivB64);

    try {
        const decrypted = await crypto.subtle.decrypt(
            { name: 'AES-GCM', iv: iv },
            key,
            ciphertext
        );

        const decoder = new TextDecoder();
        return decoder.decode(decrypted);
    } catch (e) {
        console.error('Decryption failed:', e);
        return '[Decryption Failed]';
    }
}

// Helper functions for encoding
function bufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

function base64ToBuffer(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
}

function hexToBuffer(hex) {
    const bytes = new Uint8Array(hex.length / 2);
    for (let i = 0; i < hex.length; i += 2) {
        bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
    }
    return bytes;
}

function generateRandomPassword(length = 16) {
    const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()-_=+[]{}|;:,.<>?';
    const randomValues = new Uint8Array(length);
    crypto.getRandomValues(randomValues);
    
    let password = '';
    for (let i = 0; i < length; i++) {
        password += charset[randomValues[i] % charset.length];
    }
    return password;
}

// API Calls
async function register(username, password) {
    const response = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Registration failed');
    return data;
}

async function login(username, password) {
    const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Login failed');
    
    // Store tokens and derive encryption key
    accessToken = data.accessToken;
    refreshToken = data.refreshToken;
    encryptionSalt = data.encryption_salt;
    currentUser = username;

    // Derive encryption key for client-side encryption
    encryptionKey = await deriveEncryptionKey(password, encryptionSalt);

    // Store in sessionStorage (not localStorage for security)
    sessionStorage.setItem('accessToken', accessToken);
    sessionStorage.setItem('refreshToken', refreshToken);
    sessionStorage.setItem('currentUser', username);

    return data;
}

async function addPasswordEntry(name, password, url = null) {
    if (!encryptionKey) throw new Error('Not logged in or encryption key not available');

    // Encrypt password client-side
    const encrypted = await encryptPassword(password, encryptionKey);

    const meta = url ? { url } : null;

    const response = await fetch(`${API_URL}/entries`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({
            name,
            ciphertext: encrypted.ciphertext,
            iv: encrypted.iv,
            tag: encrypted.tag || 'web_crypto_gcm',
            meta
        })
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to save password');
    return data;
}

async function getPasswordEntries() {
    if (!accessToken) throw new Error('Not logged in');

    const response = await fetch(`${API_URL}/entries`, {
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch passwords');
    return data.entries;
}

// Event Handlers
document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('register-username').value;
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-password-confirm').value;

    if (password !== confirmPassword) {
        showAlert('Passwords do not match', 'error');
        return;
    }

    if (password.length < 8) {
        showAlert('Password must be at least 8 characters', 'error');
        return;
    }

    try {
        await register(username, password);
        showAlert('Account created successfully! Please login.', 'success');
        switchTab('login');
        document.getElementById('register-form').reset();
    } catch (error) {
        showAlert(error.message, 'error');
    }
});

document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    try {
        await login(username, password);
        showAlert(`Welcome back, ${username}!`, 'success');
        
        // Update UI
        document.getElementById('not-logged-in').classList.add('hidden');
        document.getElementById('vault-content').classList.remove('hidden');
        
        // Load passwords
        await loadPasswords();
        
        document.getElementById('login-form').reset();
    } catch (error) {
        showAlert(error.message, 'error');
    }
});

document.getElementById('add-password-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const name = document.getElementById('entry-name').value;
    const password = document.getElementById('entry-password').value;
    const url = document.getElementById('entry-url').value;

    try {
        await addPasswordEntry(name, password, url || null);
        showAlert('Password saved successfully!', 'success');
        document.getElementById('add-password-form').reset();
        await loadPasswords();
    } catch (error) {
        showAlert(error.message, 'error');
    }
});

async function loadPasswords() {
    try {
        const entries = await getPasswordEntries();
        const container = document.getElementById('passwords-container');
        
        if (entries.length === 0) {
            container.innerHTML = '<p>No passwords saved yet.</p>';
            return;
        }

        container.innerHTML = '';
        for (const entry of entries) {
            const div = document.createElement('div');
            div.className = 'password-item';
            
            const nameDiv = document.createElement('div');
            nameDiv.innerHTML = `
                <div class="password-item-name">${entry.name}</div>
                ${entry.meta?.url ? `<small>${entry.meta.url}</small>` : ''}
            `;

            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'password-item-actions';
            
            const viewBtn = document.createElement('button');
            viewBtn.className = 'btn btn-primary btn-small';
            viewBtn.textContent = 'View';
            viewBtn.onclick = async () => {
                const decrypted = await decryptPassword(entry.ciphertext, entry.iv, encryptionKey);
                alert(`Password for ${entry.name}:\n\n${decrypted}`);
            };

            const copyBtn = document.createElement('button');
            copyBtn.className = 'btn btn-secondary btn-small';
            copyBtn.textContent = 'Copy';
            copyBtn.onclick = async () => {
                const decrypted = await decryptPassword(entry.ciphertext, entry.iv, encryptionKey);
                await navigator.clipboard.writeText(decrypted);
                showAlert('Password copied to clipboard!', 'success');
            };

            actionsDiv.appendChild(viewBtn);
            actionsDiv.appendChild(copyBtn);

            div.appendChild(nameDiv);
            div.appendChild(actionsDiv);
            container.appendChild(div);
        }
    } catch (error) {
        showAlert(error.message, 'error');
    }
}

function generatePassword() {
    const password = generateRandomPassword(20);
    document.getElementById('entry-password').value = password;
    showAlert('Secure password generated!', 'success');
}

// Check session on load
window.addEventListener('load', async () => {
    const storedToken = sessionStorage.getItem('accessToken');
    const storedUser = sessionStorage.getItem('currentUser');
    
    if (storedToken && storedUser) {
        accessToken = storedToken;
        refreshToken = sessionStorage.getItem('refreshToken');
        currentUser = storedUser;
        
        // Note: We can't restore encryptionKey without master password
        showAlert('Session found, but please login again for security', 'error');
    }
});
