# SecureAuth - Python Authentication Web Application

A modern, full-stack Authentication system built with **Python (Flask)** and **SQLite**, featuring a modern UI with both **Register** (Name, Email, Password) and **Sign In** capabilities.

---

## ✨ Key Features

1. **User Registration**:
   - Fields: **Full Name**, **Email Address**, **Password**, **Confirm Password**, and **Terms of Service**.
   - Real-time client-side and server-side input validation (Name length, Email regex, Password match).
   - Real-time email availability checker.
   - Dynamic interactive **Password Strength Meter** with requirement checklist.

2. **User Sign In**:
   - Secure authentication with salted and hashed passwords (using PBKDF2 / SHA-256 via Werkzeug).
   - "Remember Me" session persistence (7-day cookie session).
   - Show / Hide password visibility toggling.
   - Password reset simulation modal.

3. **User Dashboard**:
   - Protected route (`/dashboard`) accessible only to logged-in sessions.
   - Displays user details: Full Name, Email, User ID, and Registration Date.
   - Logout functionality with session clearing.

4. **Modern UI / UX**:
   - Glassmorphism design with ambient animated glowing orbs.
   - Dark / Light mode toggle with `localStorage` memory.
   - Fluid tab slider switching between Sign In and Register.
   - Dynamic Toast notifications and error animations.

---

## 🚀 How to Run

### Option 1: Double Click `run.bat`
Simply double-click the [`run.bat`](file:///c:/Users/patel/OneDrive/Desktop/abc/run.bat) file in this directory.

### Option 2: Command Line (PowerShell / Terminal)
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the application
python app.py
```

Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 📁 Project Structure

```
abc/
├── app.py                  # Main Flask application & routing
├── database.py             # SQLite database operations & schema
├── requirements.txt        # Python package dependencies
├── run.bat                 # One-click Windows runner
├── users.db                # SQLite database (auto-created on startup)
├── static/
│   ├── css/
│   │   └── style.css       # Design tokens, theme modes, glassmorphism & animations
│   └── js/
│       └── app.js          # Tab switching, password strength meter, AJAX & validation
└── templates/
    ├── auth.html           # Sign In & Register combined interface
    └── dashboard.html      # Protected user dashboard
```

---

## 🔒 Security Highlights
- **Password Hashing**: Never stores raw passwords. Passwords are securely hashed with PBKDF2-HMAC-SHA256.
- **SQL Injection Prevention**: Uses parameterized queries throughout SQLite calls.
- **Session Security**: Cryptographically signed cookie sessions with configurable secret keys.
