// Login Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    initializeLogin();
});

function initializeLogin() {
    setupEventListeners();
    checkRememberedLogin();
    setupFormValidation();
}

function setupEventListeners() {
    // Form submission
    const loginForm = document.getElementById('loginForm');
    loginForm.addEventListener('submit', handleLogin);
    
    // Password toggle
    const passwordToggle = document.getElementById('passwordToggle');
    passwordToggle.addEventListener('click', togglePasswordVisibility);
    
    // Enter key handling
    document.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const loginBtn = document.getElementById('loginBtn');
            if (!loginBtn.disabled) {
                loginForm.dispatchEvent(new Event('submit'));
            }
        }
    });
    
    // Input validation on blur
    const inputs = document.querySelectorAll('.form-input');
    inputs.forEach(input => {
        input.addEventListener('blur', validateInput);
        input.addEventListener('input', clearInputError);
    });
}

function setupFormValidation() {
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    
    // Real-time validation
    usernameInput.addEventListener('input', function() {
        validateUsername(this.value);
    });
    
    passwordInput.addEventListener('input', function() {
        validatePassword(this.value);
    });
}

function validateUsername(username) {
    const input = document.getElementById('username');
    
    if (!username) {
        setInputError(input, 'Vui lòng nhập tên đăng nhập');
        return false;
    }
    
    if (username.length < 3) {
        setInputError(input, 'Tên đăng nhập phải có ít nhất 3 ký tự');
        return false;
    }
    
    clearInputError(input);
    return true;
}

function validatePassword(password) {
    const input = document.getElementById('password');
    
    if (!password) {
        setInputError(input, 'Vui lòng nhập mật khẩu');
        return false;
    }
    
    if (password.length < 4) {
        setInputError(input, 'Mật khẩu phải có ít nhất 4 ký tự');
        return false;
    }
    
    clearInputError(input);
    return true;
}

function setInputError(input, message) {
    input.style.borderColor = '#f44336';
    input.style.boxShadow = '0 0 0 3px rgba(244, 67, 54, 0.1)';
    
    // Remove existing error message
    const existingError = input.parentNode.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }
    
    // Add error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.style.color = '#f44336';
    errorDiv.style.fontSize = '12px';
    errorDiv.style.marginTop = '5px';
    errorDiv.textContent = message;
    input.parentNode.appendChild(errorDiv);
}

function clearInputError(input) {
    if (typeof input === 'object' && input.target) {
        input = input.target;
    }
    
    input.style.borderColor = '';
    input.style.boxShadow = '';
    
    const errorMessage = input.parentNode.querySelector('.error-message');
    if (errorMessage) {
        errorMessage.remove();
    }
}

function validateInput(e) {
    const input = e.target;
    const value = input.value.trim();
    
    if (input.id === 'username') {
        validateUsername(value);
    } else if (input.id === 'password') {
        validatePassword(value);
    }
}

function togglePasswordVisibility() {
    const passwordInput = document.getElementById('password');
    const eyeIcon = document.querySelector('.eye-icon');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        eyeIcon.innerHTML = `
            <path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z"/>
        `;
    } else {
        passwordInput.type = 'password';
        eyeIcon.innerHTML = `
            <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
        `;
    }
}

function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const rememberMe = document.getElementById('rememberMe').checked;
    
    // Validate inputs
    const isUsernameValid = validateUsername(username);
    const isPasswordValid = validatePassword(password);
    
    if (!isUsernameValid || !isPasswordValid) {
        showAlert('Vui lòng kiểm tra lại thông tin đăng nhập', 'error');
        return;
    }
    
    // Show loading state
    setLoadingState(true);
    
    // Create login data
    const loginData = {
        username: username,
        password: password,
        remember_me: rememberMe
    };
    
    // Send login request
    fetch('/api/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(loginData)
    })
    .then(response => response.json())
    .then(data => {
        setLoadingState(false);
        
        if (data.success) {
            showAlert('Đăng nhập thành công!', 'success');
            
            // Save login info if remember me is checked
            if (rememberMe) {
                localStorage.setItem('rememberedUsername', username);
                localStorage.setItem('rememberLogin', 'true');
            } else {
                localStorage.removeItem('rememberedUsername');
                localStorage.removeItem('rememberLogin');
            }
            
            // Save session token
            if (data.token) {
                sessionStorage.setItem('authToken', data.token);
                localStorage.setItem('authToken', data.token);
            }
            
            // Redirect to main page after short delay
            console.log('Redirecting to main page...');
            window.location.href = '/';
            
        } else {
            showAlert(data.message || 'Tên đăng nhập hoặc mật khẩu không đúng', 'error');
            
            // Shake animation for error
            const container = document.querySelector('.login-container');
            container.style.animation = 'shake 0.5s ease-in-out';
            setTimeout(() => {
                container.style.animation = '';
            }, 500);
        }
    })
    .catch(error => {
        setLoadingState(false);
        console.error('Login error:', error);
        showAlert('Lỗi kết nối. Vui lòng thử lại sau.', 'error');
    });
}

function setLoadingState(loading) {
    const loginBtn = document.getElementById('loginBtn');
    const btnText = loginBtn.querySelector('.btn-text');
    const btnLoading = loginBtn.querySelector('.btn-loading');
    
    if (loading) {
        loginBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoading.style.display = 'flex';
    } else {
        loginBtn.disabled = false;
        btnText.style.display = 'block';
        btnLoading.style.display = 'none';
    }
}
function checkRememberedLogin() {
    const rememberLogin = localStorage.getItem('rememberLogin');
    const rememberedUsername = localStorage.getItem('rememberedUsername');
    
    if (rememberLogin === 'true' && rememberedUsername) {
        document.getElementById('username').value = rememberedUsername;
        document.getElementById('rememberMe').checked = true;
    }
    
    // Check if already logged in - chỉ kiểm tra token, không redirect
    const authToken = sessionStorage.getItem('authToken') || localStorage.getItem('authToken');
    if (authToken) {
        // Verify token với server, nhưng không redirect từ đây
        fetch('/api/verify-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.valid) {
                // Chỉ hiển thị message, không redirect
                showAlert('Bạn đã đăng nhập. Click vào đây để vào trang chính.', 'info');
                
                // Thêm click handler cho alert để redirect
                setTimeout(() => {
                    const alertDiv = document.querySelector('.alert-info');
                    if (alertDiv) {
                        alertDiv.style.cursor = 'pointer';
                        alertDiv.onclick = function() {
                            window.location.href = '/';
                        };
                    }
                }, 100);
            } else {
                // Token không hợp lệ, xóa token
                sessionStorage.removeItem('authToken');
                localStorage.removeItem('authToken');
            }
        })
        .catch(error => {
            console.log('Token verification failed:', error);
            // Remove invalid token
            sessionStorage.removeItem('authToken');
            localStorage.removeItem('authToken');
        });
    }
}
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alertContainer');
    
    // Remove existing alerts
    alertContainer.innerHTML = '';
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    alertContainer.appendChild(alertDiv);
    
    // Auto remove alert after 4 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => {
                alertDiv.remove();
            }, 300);
        }
    }, 4000);
}

// Add shake animation for error states
const shakeCSS = `
@keyframes shake {
    0%, 20%, 40%, 60%, 80%, 100% {
        transform: translateX(0);
    }
    10%, 30%, 50%, 70%, 90% {
        transform: translateX(-10px);
    }
}

@keyframes slideOutRight {
    from {
        opacity: 1;
        transform: translateX(0);
    }
    to {
        opacity: 0;
        transform: translateX(100%);
    }
}
`;

// Inject CSS
const style = document.createElement('style');
style.textContent = shakeCSS;
document.head.appendChild(style);