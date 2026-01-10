/**
 * RAG Chat Component for CASTOR ELECCIONES
 * Provides an AI assistant with context from indexed analyses
 */

class RAGChat {
    constructor(options = {}) {
        this.containerId = options.containerId || 'rag-chat-container';
        this.apiBase = options.apiBase || '/api';
        this.conversationId = null;
        this.conversationHistory = [];
        this.isLoading = false;

        // Configuration
        this.config = {
            topK: options.topK || 5,
            minScore: options.minScore || 0.3,
            placeholder: options.placeholder || 'Pregunta sobre tus análisis...',
            welcomeMessage: options.welcomeMessage || '¡Hola! Soy CASTOR AI. Puedo responder preguntas sobre los análisis de sentimiento y tendencias que has realizado. ¿En qué puedo ayudarte?'
        };

        this.init();
    }

    init() {
        this.render();
        this.attachEventListeners();
        this.addMessage('assistant', this.config.welcomeMessage);
        this.loadStats();
    }

    render() {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error(`Container #${this.containerId} not found`);
            return;
        }

        container.innerHTML = `
            <div class="rag-chat">
                <div class="rag-chat-header">
                    <div class="rag-chat-title">
                        <span class="rag-chat-icon">🤖</span>
                        <span>CASTOR AI Assistant</span>
                    </div>
                    <div class="rag-chat-stats" id="rag-stats">
                        <span class="stat-item">📚 <span id="docs-count">0</span> documentos</span>
                    </div>
                </div>

                <div class="rag-chat-messages" id="rag-messages">
                    <!-- Messages will be inserted here -->
                </div>

                <div class="rag-chat-sources" id="rag-sources" style="display: none;">
                    <div class="sources-header">
                        <span>📎 Fuentes utilizadas</span>
                        <button class="sources-close" onclick="ragChat.hideSources()">×</button>
                    </div>
                    <div class="sources-list" id="rag-sources-list"></div>
                </div>

                <div class="rag-chat-input-area">
                    <input
                        type="text"
                        id="rag-input"
                        class="rag-chat-input"
                        placeholder="${this.config.placeholder}"
                        autocomplete="off"
                    />
                    <button id="rag-send-btn" class="rag-chat-send">
                        <span id="send-icon">➤</span>
                        <span id="loading-icon" style="display: none;">⏳</span>
                    </button>
                </div>

                <div class="rag-chat-suggestions" id="rag-suggestions">
                    <button class="suggestion-btn" data-query="¿Cuáles son los temas con mejor recepción?">
                        📊 Temas positivos
                    </button>
                    <button class="suggestion-btn" data-query="¿Qué recomendaciones estratégicas hay?">
                        💡 Recomendaciones
                    </button>
                    <button class="suggestion-btn" data-query="¿Cuál es el sentimiento general?">
                        😊 Sentimiento
                    </button>
                </div>
            </div>
        `;

        this.injectStyles();
    }

    injectStyles() {
        if (document.getElementById('rag-chat-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'rag-chat-styles';
        styles.textContent = `
            .rag-chat {
                display: flex;
                flex-direction: column;
                height: 100%;
                max-height: 600px;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                background: #fff;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }

            .rag-chat-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 16px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 12px 12px 0 0;
            }

            .rag-chat-title {
                display: flex;
                align-items: center;
                gap: 8px;
                font-weight: 600;
            }

            .rag-chat-icon {
                font-size: 1.2em;
            }

            .rag-chat-stats {
                font-size: 0.85em;
                opacity: 0.9;
            }

            .rag-chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
                background: #f8f9fa;
            }

            .chat-message {
                max-width: 85%;
                margin-bottom: 12px;
                padding: 10px 14px;
                border-radius: 16px;
                line-height: 1.4;
                animation: fadeIn 0.3s ease;
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .chat-message.user {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                margin-left: auto;
                border-bottom-right-radius: 4px;
            }

            .chat-message.assistant {
                background: white;
                color: #333;
                border: 1px solid #e0e0e0;
                border-bottom-left-radius: 4px;
            }

            .chat-message.assistant .sources-link {
                display: block;
                margin-top: 8px;
                font-size: 0.85em;
                color: #667eea;
                cursor: pointer;
            }

            .chat-message.assistant .sources-link:hover {
                text-decoration: underline;
            }

            .rag-chat-sources {
                padding: 12px;
                background: #f0f0f0;
                border-top: 1px solid #e0e0e0;
                max-height: 200px;
                overflow-y: auto;
            }

            .sources-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
                font-weight: 600;
                font-size: 0.9em;
            }

            .sources-close {
                background: none;
                border: none;
                font-size: 1.2em;
                cursor: pointer;
                padding: 0 4px;
            }

            .source-item {
                background: white;
                padding: 8px 12px;
                margin-bottom: 8px;
                border-radius: 8px;
                font-size: 0.85em;
                border-left: 3px solid #667eea;
            }

            .source-item .source-type {
                font-weight: 600;
                color: #667eea;
            }

            .source-item .source-score {
                float: right;
                color: #888;
                font-size: 0.85em;
            }

            .source-item .source-preview {
                color: #666;
                margin-top: 4px;
                font-size: 0.9em;
            }

            .rag-chat-input-area {
                display: flex;
                padding: 12px;
                background: white;
                border-top: 1px solid #e0e0e0;
            }

            .rag-chat-input {
                flex: 1;
                padding: 10px 14px;
                border: 1px solid #e0e0e0;
                border-radius: 20px;
                font-size: 14px;
                outline: none;
                transition: border-color 0.2s;
            }

            .rag-chat-input:focus {
                border-color: #667eea;
            }

            .rag-chat-send {
                margin-left: 8px;
                padding: 10px 16px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 20px;
                cursor: pointer;
                transition: transform 0.2s;
            }

            .rag-chat-send:hover {
                transform: scale(1.05);
            }

            .rag-chat-send:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }

            .rag-chat-suggestions {
                display: flex;
                gap: 8px;
                padding: 8px 12px;
                background: white;
                border-radius: 0 0 12px 12px;
                overflow-x: auto;
            }

            .suggestion-btn {
                flex-shrink: 0;
                padding: 6px 12px;
                background: #f0f0f0;
                border: none;
                border-radius: 16px;
                font-size: 0.85em;
                cursor: pointer;
                transition: background 0.2s;
            }

            .suggestion-btn:hover {
                background: #e0e0e0;
            }

            .typing-indicator {
                display: flex;
                gap: 4px;
                padding: 10px 14px;
            }

            .typing-dot {
                width: 8px;
                height: 8px;
                background: #667eea;
                border-radius: 50%;
                animation: typing 1.4s infinite;
            }

            .typing-dot:nth-child(2) { animation-delay: 0.2s; }
            .typing-dot:nth-child(3) { animation-delay: 0.4s; }

            @keyframes typing {
                0%, 60%, 100% { transform: translateY(0); }
                30% { transform: translateY(-10px); }
            }
        `;
        document.head.appendChild(styles);
    }

    attachEventListeners() {
        const input = document.getElementById('rag-input');
        const sendBtn = document.getElementById('rag-send-btn');
        const suggestions = document.querySelectorAll('.suggestion-btn');

        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !this.isLoading) {
                this.sendMessage();
            }
        });

        sendBtn.addEventListener('click', () => {
            if (!this.isLoading) {
                this.sendMessage();
            }
        });

        suggestions.forEach(btn => {
            btn.addEventListener('click', () => {
                const query = btn.dataset.query;
                document.getElementById('rag-input').value = query;
                this.sendMessage();
            });
        });
    }

    async sendMessage() {
        const input = document.getElementById('rag-input');
        const message = input.value.trim();

        if (!message) return;

        // Add user message
        this.addMessage('user', message);
        input.value = '';

        // Show loading
        this.setLoading(true);
        this.showTypingIndicator();

        // Add to history
        this.conversationHistory.push({
            role: 'user',
            content: message
        });

        try {
            const response = await fetch(`${this.apiBase}/chat/rag`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.conversationId,
                    conversation_history: this.conversationHistory.slice(-6),
                    top_k: this.config.topK,
                    min_score: this.config.minScore
                })
            });

            const data = await response.json();

            this.hideTypingIndicator();

            if (data.success) {
                this.conversationId = data.conversation_id;
                this.addMessage('assistant', data.answer, data.sources);

                // Add to history
                this.conversationHistory.push({
                    role: 'assistant',
                    content: data.answer
                });
            } else {
                this.addMessage('assistant', `Lo siento, ocurrió un error: ${data.error}`);
            }

        } catch (error) {
            console.error('RAG Chat error:', error);
            this.hideTypingIndicator();
            this.addMessage('assistant', 'Lo siento, hubo un error de conexión. Por favor intenta de nuevo.');
        } finally {
            this.setLoading(false);
        }
    }

    addMessage(role, content, sources = []) {
        const messagesContainer = document.getElementById('rag-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}`;

        let html = content.replace(/\n/g, '<br>');

        if (role === 'assistant' && sources.length > 0) {
            html += `<span class="sources-link" onclick="ragChat.showSources(${JSON.stringify(sources).replace(/"/g, '&quot;')})">📎 Ver ${sources.length} fuentes</span>`;
        }

        messageDiv.innerHTML = html;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    showTypingIndicator() {
        const messagesContainer = document.getElementById('rag-messages');
        const indicator = document.createElement('div');
        indicator.id = 'typing-indicator';
        indicator.className = 'chat-message assistant';
        indicator.innerHTML = `
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        messagesContainer.appendChild(indicator);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    setLoading(loading) {
        this.isLoading = loading;
        const sendIcon = document.getElementById('send-icon');
        const loadingIcon = document.getElementById('loading-icon');
        const sendBtn = document.getElementById('rag-send-btn');

        sendIcon.style.display = loading ? 'none' : 'inline';
        loadingIcon.style.display = loading ? 'inline' : 'none';
        sendBtn.disabled = loading;
    }

    showSources(sources) {
        const sourcesContainer = document.getElementById('rag-sources');
        const sourcesList = document.getElementById('rag-sources-list');

        sourcesList.innerHTML = sources.map(s => `
            <div class="source-item">
                <span class="source-type">${this.getSourceTypeLabel(s.type)}</span>
                <span class="source-score">${Math.round(s.score * 100)}% relevante</span>
                <div class="source-preview">${s.preview}</div>
            </div>
        `).join('');

        sourcesContainer.style.display = 'block';
    }

    hideSources() {
        document.getElementById('rag-sources').style.display = 'none';
    }

    getSourceTypeLabel(type) {
        const labels = {
            'executive_summary': '📋 Resumen Ejecutivo',
            'topic': '📌 Tema',
            'sentiment': '😊 Sentimiento',
            'strategic_plan': '🎯 Plan Estratégico',
            'forecast': '📈 Pronóstico'
        };
        return labels[type] || '📄 Documento';
    }

    async loadStats() {
        try {
            const response = await fetch(`${this.apiBase}/chat/rag/stats`);
            const data = await response.json();

            if (data.success) {
                document.getElementById('docs-count').textContent = data.documents_indexed;
            }
        } catch (error) {
            console.error('Error loading RAG stats:', error);
        }
    }

    // Public method to index analysis data
    async indexAnalysis(analysisId, analysisData, metadata = {}) {
        try {
            const response = await fetch(`${this.apiBase}/chat/rag/index`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    analysis_id: analysisId,
                    analysis_data: analysisData,
                    metadata: metadata
                })
            });

            const data = await response.json();

            if (data.success) {
                console.log(`Indexed ${data.documents_created} documents for analysis ${analysisId}`);
                this.loadStats(); // Refresh stats
            }

            return data;
        } catch (error) {
            console.error('Error indexing analysis:', error);
            throw error;
        }
    }

    // Clear conversation
    clearConversation() {
        this.conversationHistory = [];
        this.conversationId = null;
        document.getElementById('rag-messages').innerHTML = '';
        this.addMessage('assistant', this.config.welcomeMessage);
    }
}

// Global instance
let ragChat = null;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('rag-chat-container');
    if (container) {
        ragChat = new RAGChat();
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RAGChat;
}
