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
        // 检查是否有文档关联
        let hasDocs = false;
        if (currentConversationId) {
            const docsResponse = await fetch(`/api/conversation/${currentConversationId}/documents`, {
                headers: {
                    'Authorization': `Bearer ${accessToken}`
                }
            });
            if (docsResponse.ok) {
                const docsData = await docsResponse.json();
                hasDocs = docsData.documents && docsData.documents.length > 0;
            }
        }

        const response = await fetch('/api/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ 
                message: message,
                conversation_id: currentConversationId,
                use_rag: hasDocs // 告诉后端是否使用RAG
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
                            
                            // 标记RAG生成的回复
                            if (data.rag_sources) {
                                const ragInfo = document.createElement('div');
                                ragInfo.className = 'rag-info';
                                ragInfo.textContent = '基于上传文档生成';
                                currentMessageDiv.appendChild(ragInfo);
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
    fileInput.multiple = true; // 支持多文件选择
    document.body.appendChild(fileInput);

    // 创建上传按钮
    const uploadButton = document.createElement('button');
    uploadButton.className = 'file-upload-button';
    uploadButton.innerHTML = '<i class="fas fa-upload"></i> 上传文件';
    uploadButton.onclick = () => {
        if (!currentConversationId) {
            // 自动创建新会话
            createNewConversation().then(() => {
                fileInput.click();
            });
            return;
        }
        fileInput.click();
    };

    // 创建清除按钮
    const clearButton = document.createElement('button');
    clearButton.className = 'clear-docs-button';
    clearButton.innerHTML = '<i class="fas fa-trash"></i> 清除文档';
    clearButton.onclick = () => {
        if (!currentConversationId) {
            appendMessage('没有活动的会话', false);
            return;
        }
        if (confirm('确定要清除当前会话的所有文档吗？')) {
            clearConversationDocuments(currentConversationId);
        }
    };

    // 文件选择处理
    fileInput.onchange = async (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        // 显示上传状态
        const statusMessage = appendMessage(`正在上传 ${files.length} 个文件...`, false);
        
        // 限制文件大小 (5MB)
        const maxSize = 5 * 1024 * 1024;
        let successCount = 0;
        
        for (const file of files) {
            if (file.size > maxSize) {
                appendMessage(`文件 ${file.name} 超过5MB限制，已跳过`, false);
                continue;
            }
            
            try {
                await uploadDocument(file, currentConversationId);
                successCount++;
            } catch (error) {
                console.error(`Error uploading ${file.name}:`, error);
            }
        }
        
        // 更新状态消息
        statusMessage.textContent = `文件上传完成 (${successCount}/${files.length} 成功)`;
    };

    // 添加到输入容器
    const inputContainer = document.getElementById('input-container');
    const buttonGroup = document.createElement('div');
    buttonGroup.className = 'file-button-group';
    buttonGroup.appendChild(uploadButton);
    buttonGroup.appendChild(clearButton);
    inputContainer.insertBefore(buttonGroup, inputContainer.firstChild);
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
    
    // 加载会话文档列表
    await loadConversationDocuments();
}

async function loadConversationDocuments() {
    if (!currentConversationId) return;
    
    try {
        const response = await fetch(`/api/conversation/${currentConversationId}/documents`, {
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });
        
        if (!response.ok) return;
        
        const data = await response.json();
        const docsList = document.getElementById('documents-list');
        
        if (!docsList) {
            // 创建文档列表容器
            const sidebar = document.getElementById('sidebar');
            const docsContainer = document.createElement('div');
            docsContainer.id = 'documents-container';
            docsContainer.innerHTML = `
                <h3>会话文档</h3>
                <div id="documents-list"></div>
            `;
            sidebar.appendChild(docsContainer);
        }
        
        const docsListElement = document.getElementById('documents-list');
        docsListElement.innerHTML = '';
        
        if (data.documents && data.documents.length > 0) {
            data.documents.forEach(doc => {
                const docItem = document.createElement('div');
                docItem.className = 'document-item';
                docItem.innerHTML = `
                    <span>${doc.filename}</span>
                    <button onclick="removeDocument('${currentConversationId}', '${doc.id}')">
                        <i class="fas fa-times"></i>
                    </button>
                `;
                docsListElement.appendChild(docItem);
            });
        } else {
            docsListElement.innerHTML = '<p>没有上传的文档</p>';
        }
    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

async function removeDocument(conversationId, docId) {
    if (!confirm('确定要删除这个文档吗？')) return;
    
    try {
        const response = await fetch(`/api/conversation/${conversationId}/documents/remove`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ document_id: docId })
        });
        
        if (!response.ok) {
            throw new Error('删除失败');
        }
        
        await loadConversationDocuments();
        appendMessage('文档已删除', false);
    } catch (error) {
        console.error('Error removing document:', error);
        appendMessage(`删除文档失败: ${error.message}`, false);
    }
}

async function createNewConversation() {
    try {
        const response = await fetch('/api/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ 
                message: '新会话已创建',
                conversation_id: null
            })
        });

        if (!response.ok) {
            throw new Error('创建会话失败');
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
                        if (data.conversation_id) {
                            currentConversationId = data.conversation_id;
                            return;
                        }
                    } catch (e) {
                        console.error('Error parsing SSE data:', e);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Error creating conversation:', error);
        appendMessage(`创建会话失败: ${error.message}`, false);
    }
}

// 初始化界面
initializeUI();