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
    document.getElementById('sidebar').style.display = 'none';
}

function showChat() {
    document.getElementById('auth-container').style.display = 'none';
    document.getElementById('chat-container').style.display = 'block';
    document.getElementById('input-container').style.display = 'flex';
    document.getElementById('sidebar').style.display = 'block';
}

// 检查登录状态并初始化界面
async function initializeUI() {
    if (accessToken) {
        showChat();
        setupFileUpload();
        await loadChatHistory();
    } else {
        showLogin();
    }
}

// 聊天相关函数
function appendMessage(message, isUser = false, timestamp = null) {
    const chatContainer = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    
    if (timestamp) {
        const timeElement = document.createElement('div');
        timeElement.className = 'message-time';
        timeElement.textContent = new Date(timestamp).toLocaleString();
        messageDiv.appendChild(timeElement);
    }
    
    const contentElement = document.createElement('div');
    contentElement.className = 'message-content';
    contentElement.textContent = message;
    messageDiv.appendChild(contentElement);
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return messageDiv;
}

async function sendMessage() {
    const input = document.getElementById('prompt-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    appendMessage(message, true);
    input.value = '';
    
    currentResponse = '';
    currentMessageDiv = appendMessage('');

    try {
        const response = await fetch('/api/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ 
                message: message,
                conversation_id: currentConversationId
            })
        });

        if (!response.ok) {
            if (response.status === 401) {
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

async function uploadDocument(file, conversationId) {
    if (!file || !conversationId) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('conversation_id', conversationId);

    try {
        const response = await fetch('/api/index', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        appendMessage(`文件 ${file.name} 上传成功！`, false);
    } catch (error) {
        console.error('Error uploading document:', error);
        appendMessage(`文件上传失败: ${error.message}`, false);
    }
}

async function clearConversationDocuments(conversationId) {
    if (!conversationId) return;

    try {
        const response = await fetch(`/api/conversation/${conversationId}/documents`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        appendMessage('会话文档已清除！', false);
    } catch (error) {
        console.error('Error clearing documents:', error);
        appendMessage(`清除文档失败: ${error.message}`, false);
    }
}

function setupFileUpload() {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.txt,.pdf,.doc,.docx';
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);

    const uploadButton = document.createElement('button');
    uploadButton.textContent = '上传文件';
    uploadButton.onclick = () => {
        if (!currentConversationId) {
            appendMessage('请先发送一条消息以创建会话', false);
            return;
        }
        fileInput.click();
    };

    const clearButton = document.createElement('button');
    clearButton.textContent = '清除文档';
    clearButton.onclick = () => {
        if (!currentConversationId) {
            appendMessage('没有活动的会话', false);
            return;
        }
        clearConversationDocuments(currentConversationId);
    };

    fileInput.onchange = (e) => {
        const file = e.target.files[0];
        if (file) {
            uploadDocument(file, currentConversationId);
        }
    };

    const inputContainer = document.getElementById('input-container');
    inputContainer.insertBefore(uploadButton, inputContainer.firstChild);
    inputContainer.insertBefore(clearButton, inputContainer.firstChild);
}

// 添加回车键发送消息的功能
document.getElementById('prompt-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

async function loadChatHistory() {
    try {
        const response = await fetch('/api/history', {
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        const conversationList = document.getElementById('conversation-list');
        conversationList.innerHTML = '';

        data.history.forEach(conversation => {
            const conversationItem = document.createElement('div');
            conversationItem.className = 'conversation-item';
            
            // 显示对话摘要(取第一条消息的前20个字符)
            const summary = conversation.messages.length > 0 
                ? conversation.messages[0].content.substring(0, 20) + (conversation.messages[0].content.length > 20 ? '...' : '')
                : '空对话';
                
            conversationItem.textContent = summary;
            conversationItem.onclick = () => loadConversation(conversation);
            conversationList.appendChild(conversationItem);
        });
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

async function loadConversation(conversation) {
    const chatContainer = document.getElementById('chat-container');
    chatContainer.innerHTML = '';
    
    // 更新当前会话ID
    currentConversationId = conversation.conversation_id;
    
    // 加载消息
    conversation.messages.forEach(message => {
        appendMessage(message.content, message.role === 'user', message.created_at);
    });
}

// 初始化界面
initializeUI();