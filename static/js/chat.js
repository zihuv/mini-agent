let currentResponse = '';
let currentMessageDiv = null;
let currentConversationId = null;
let accessToken = localStorage.getItem('access_token');

// 认证相关函数
async function login() {
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    try {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch('/auth/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error('Login failed');
        }

        const data = await response.json();
        accessToken = data.access_token;
        localStorage.setItem('access_token', accessToken);
        
        // 显示聊天界面
        showChat();
    } catch (error) {
        alert('登录失败：' + error.message);
    }
}

async function register() {
    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;

    try {
        const response = await fetch('/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username,
                email,
                password
            })
        });

        if (!response.ok) {
            throw new Error('Registration failed');
        }

        const data = await response.json();
        accessToken = data.access_token;
        localStorage.setItem('access_token', accessToken);
        
        // 显示聊天界面
        showChat();
    } catch (error) {
        alert('注册失败：' + error.message);
    }
}

function logout() {
    localStorage.removeItem('access_token');
    accessToken = null;
    currentConversationId = null;
    showLogin();
}

function showRegister() {
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('register-form').style.display = 'block';
}

function showLogin() {
    document.getElementById('register-form').style.display = 'none';
    document.getElementById('login-form').style.display = 'block';
}

function showChat() {
    document.getElementById('auth-container').style.display = 'none';
    document.getElementById('chat-container').style.display = 'block';
    document.getElementById('input-container').style.display = 'flex';
}

// 检查登录状态并初始化界面
function initializeUI() {
    if (accessToken) {
        showChat();
    } else {
        showLogin();
    }
}

// 聊天相关函数
function appendMessage(message, isUser = false) {
    const chatContainer = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    messageDiv.textContent = message;
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return messageDiv;
}

async function sendMessage() {
    const input = document.getElementById('prompt-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // 显示用户消息
    appendMessage(message, true);
    
    // 清空输入框
    input.value = '';
    
    // 创建新的回复消息div
    currentResponse = '';
    currentMessageDiv = appendMessage('');

    try {
        // 创建 POST 请求到后端
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ 
                prompt: message,
                conversation_id: currentConversationId
            })
        });

        if (!response.ok) {
            if (response.status === 401) {
                // 如果是认证错误，返回登录界面
                logout();
                throw new Error('Session expired. Please login again.');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const text = decoder.decode(value);
            const lines = text.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.text) {
                            currentResponse += data.text;
                            currentMessageDiv.textContent = currentResponse;
                            if (data.conversation_id) {
                                currentConversationId = data.conversation_id;
                            }
                        } else if (data.error) {
                            currentMessageDiv.textContent = `错误: ${data.error}`;
                            currentMessageDiv.style.color = 'red';
                        }
                    } catch (e) {
                        console.error('Error parsing SSE data:', e);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Error:', error);
        currentMessageDiv.textContent = error.message || '发生错误，请重试。';
        currentMessageDiv.style.color = 'red';
    }
}

// 添加回车键发送消息的功能
document.getElementById('prompt-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// 初始化界面
initializeUI();