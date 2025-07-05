let currentResponse = '';
let currentMessageDiv = null;

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
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt: message })
        });

        if (!response.ok) {
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
        currentMessageDiv.textContent = '发生错误，请重试。';
        currentMessageDiv.style.color = 'red';
    }
}

// 添加回车键发送消息的功能
document.getElementById('prompt-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});