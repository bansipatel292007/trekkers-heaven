/**
 * AMU Authentication - Frontend Interactive Controller
 */

let currentMode = 'register';

document.addEventListener('DOMContentLoaded', () => {
    initAuthMode();
    initValidation();
    initFormSubmissions();
    initForgotPasswordModal();
    initToasts();
});

/* ==========================================
   1. Auth Mode Switching (Create account <-> Log in)
   ========================================== */
function initAuthMode() {
    currentMode = typeof INITIAL_AUTH_MODE !== 'undefined' ? INITIAL_AUTH_MODE : 'register';
    setAuthMode(currentMode, false);
}

function toggleAuthMode() {
    const nextMode = currentMode === 'register' ? 'login' : 'register';
    setAuthMode(nextMode, true);
}

function setAuthMode(mode, updateUrl = true) {
    currentMode = mode;
    const formTitle = document.getElementById('formTitle');
    const promptText = document.getElementById('promptText');
    const toggleModeLink = document.getElementById('toggleModeLink');
    const registerForm = document.getElementById('registerForm');
    const loginForm = document.getElementById('loginForm');

    if (mode === 'login') {
        if (formTitle) formTitle.innerText = 'Welcome back';
        if (promptText) promptText.innerText = "Don't have an account?";
        if (toggleModeLink) toggleModeLink.innerText = 'Sign up';
        
        if (registerForm) registerForm.classList.remove('active');
        if (loginForm) loginForm.classList.add('active');

        if (updateUrl) {
            window.history.replaceState(null, '', '?mode=login');
        }
    } else {
        if (formTitle) formTitle.innerText = 'Create an account';
        if (promptText) promptText.innerText = 'Already have an account?';
        if (toggleModeLink) toggleModeLink.innerText = 'Log in';
        
        if (loginForm) loginForm.classList.remove('active');
        if (registerForm) registerForm.classList.add('active');

        if (updateUrl) {
            window.history.replaceState(null, '', '?mode=register');
        }
    }
}

/* ==========================================
   2. Password Visibility Toggler
   ========================================== */
function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const icon = btn.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        if (icon) {
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        }
    } else {
        input.type = 'password';
        if (icon) {
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    }
}

/* ==========================================
   3. Live Validation
   ========================================== */
function isValidEmail(email) {
    return /^[\w\.-]+@[\w\.-]+\.\w+$/.test(email.trim());
}

function initValidation() {
    const regFirstName = document.getElementById('regFirstName');
    const regFirstNameError = document.getElementById('regFirstNameError');
    if (regFirstName) {
        regFirstName.addEventListener('input', () => {
            if (regFirstName.value.trim().length >= 1) {
                regFirstName.classList.remove('is-invalid');
                if (regFirstNameError) regFirstNameError.innerText = '';
            }
        });
    }

    const regEmail = document.getElementById('regEmail');
    const regEmailError = document.getElementById('regEmailError');
    if (regEmail) {
        regEmail.addEventListener('input', () => {
            const email = regEmail.value.trim();
            if (!email || isValidEmail(email)) {
                regEmail.classList.remove('is-invalid');
                if (regEmailError) regEmailError.innerText = '';
            }
        });
    }
}

/* ==========================================
   4. AJAX Form Submissions
   ========================================== */
function initFormSubmissions() {
    // REGISTER FORM SUBMIT
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const firstNameInput = document.getElementById('regFirstName');
            const lastNameInput = document.getElementById('regLastName');
            const emailInput = document.getElementById('regEmail');
            const passwordInput = document.getElementById('regPassword');
            const submitBtn = document.getElementById('registerSubmitBtn');

            const firstNameErr = document.getElementById('regFirstNameError');
            const emailErr = document.getElementById('regEmailError');
            const pwdErr = document.getElementById('regPasswordError');

            if (firstNameErr) firstNameErr.innerText = '';
            if (emailErr) emailErr.innerText = '';
            if (pwdErr) pwdErr.innerText = '';

            const firstName = firstNameInput ? firstNameInput.value.trim() : '';
            const lastName = lastNameInput ? lastNameInput.value.trim() : '';
            const fullName = lastName ? `${firstName} ${lastName}` : firstName;
            const email = emailInput ? emailInput.value.trim() : '';
            const password = passwordInput ? passwordInput.value : '';

            let hasError = false;

            if (!firstName) {
                if (firstNameErr) firstNameErr.innerText = 'Please enter your first name.';
                if (firstNameInput) firstNameInput.classList.add('is-invalid');
                hasError = true;
            }
            if (!isValidEmail(email)) {
                if (emailErr) emailErr.innerText = 'Please enter a valid email address.';
                if (emailInput) emailInput.classList.add('is-invalid');
                hasError = true;
            }
            if (!password) {
                if (pwdErr) pwdErr.innerText = 'Please enter a password.';
                if (passwordInput) passwordInput.classList.add('is-invalid');
                hasError = true;
            }

            if (hasError) {
                triggerShake(registerForm);
                return;
            }

            setButtonLoading(submitBtn, true);

            try {
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: fullName,
                        first_name: firstName,
                        last_name: lastName,
                        email: email,
                        password: password,
                        confirm_password: password
                    })
                });

                const data = await response.json();
                setButtonLoading(submitBtn, false);

                if (response.ok && data.success) {
                    showToast(data.message, 'success');
                    setTimeout(() => {
                        window.location.href = data.redirect || '/dashboard';
                    }, 500);
                } else {
                    showToast(data.message || 'Registration failed.', 'danger');
                    triggerShake(registerForm);
                }
            } catch (err) {
                setButtonLoading(submitBtn, false);
                registerForm.submit();
            }
        });
    }

    // LOGIN FORM SUBMIT
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const emailInput = document.getElementById('loginEmail');
            const passwordInput = document.getElementById('loginPassword');
            const submitBtn = document.getElementById('loginSubmitBtn');
            const emailErr = document.getElementById('loginEmailError');
            const pwdErr = document.getElementById('loginPasswordError');

            if (emailErr) emailErr.innerText = '';
            if (pwdErr) pwdErr.innerText = '';

            const email = emailInput ? emailInput.value.trim() : '';
            const password = passwordInput ? passwordInput.value : '';

            let hasError = false;
            if (!email) {
                if (emailErr) emailErr.innerText = 'Please enter your email.';
                if (emailInput) emailInput.classList.add('is-invalid');
                hasError = true;
            }
            if (!password) {
                if (pwdErr) pwdErr.innerText = 'Please enter your password.';
                if (passwordInput) passwordInput.classList.add('is-invalid');
                hasError = true;
            }

            if (hasError) {
                triggerShake(loginForm);
                return;
            }

            setButtonLoading(submitBtn, true);

            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });

                const data = await response.json();
                setButtonLoading(submitBtn, false);

                if (response.ok && data.success) {
                    showToast(data.message, 'success');
                    setTimeout(() => {
                        window.location.href = data.redirect || '/dashboard';
                    }, 500);
                } else {
                    showToast(data.message || 'Invalid email or password.', 'danger');
                    triggerShake(loginForm);
                }
            } catch (err) {
                setButtonLoading(submitBtn, false);
                loginForm.submit();
            }
        });
    }
}

function setButtonLoading(btn, isLoading) {
    if (!btn) return;
    if (isLoading) {
        btn.classList.add('loading');
        btn.disabled = true;
    } else {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

function triggerShake(element) {
    element.classList.remove('shake');
    void element.offsetWidth;
    element.classList.add('shake');
}

/* ==========================================
   5. Toast Notifications (Max 3 Seconds Lifetime)
   ========================================== */
function initToasts() {
    const existingToasts = document.querySelectorAll('.toast-container .toast');
    existingToasts.forEach(toast => {
        const closeBtn = toast.querySelector('.toast-close');
        if (closeBtn) {
            closeBtn.onclick = () => {
                toast.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(-10px)';
                setTimeout(() => toast.remove(), 200);
            };
        }

        // Auto dismiss server rendered toasts in max 3 seconds (3000ms)
        setTimeout(() => {
            if (toast && toast.parentElement) {
                toast.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(-10px)';
                setTimeout(() => toast.remove(), 250);
            }
        }, 3000);
    });
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type} show`;

    let iconClass = 'fa-solid fa-circle-info';
    if (type === 'success') iconClass = 'fa-solid fa-circle-check';
    else if (type === 'danger') iconClass = 'fa-solid fa-circle-xmark';
    else if (type === 'warning') iconClass = 'fa-solid fa-triangle-exclamation';

    toast.innerHTML = `
        <div class="toast-icon"><i class="${iconClass}"></i></div>
        <div class="toast-text">${message}</div>
        <button class="toast-close">&times;</button>
    `;

    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        setTimeout(() => toast.remove(), 200);
    });

    container.appendChild(toast);

    // Auto dismiss in max 3 seconds (3000ms)
    setTimeout(() => {
        if (toast && toast.parentElement) {
            toast.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-10px)';
            setTimeout(() => toast.remove(), 250);
        }
    }, 3000);
}

/* ==========================================
   6. Forgot Password & Social Login Handlers
   ========================================== */
function initForgotPasswordModal() {
    // modal is opened via onclick in HTML
}

function openForgotPasswordModal() {
    const modal = document.getElementById('forgotPasswordModal');
    if (modal) modal.classList.add('active');
}

function closeForgotPasswordModal() {
    const modal = document.getElementById('forgotPasswordModal');
    if (modal) modal.classList.remove('active');
}

function sendPasswordReset() {
    const resetEmail = document.getElementById('resetEmail');
    if (!resetEmail || !isValidEmail(resetEmail.value)) {
        showToast('Please enter a valid email address.', 'warning');
        return;
    }
    showToast(`Password reset link sent to ${resetEmail.value}!`, 'success');
    closeForgotPasswordModal();
}

function demoSocialLogin(provider) {
    showToast(`${provider} login simulation started!`, 'info');
}
