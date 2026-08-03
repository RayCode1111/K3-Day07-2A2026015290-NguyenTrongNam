// Initialize Lucide icons
lucide.createIcons();

// --- DOM Elements ---
// Navigation
const navBtns = document.querySelectorAll('.nav-btn');
const tabContents = document.querySelectorAll('.tab-content');

// Theme
const themeBtn = document.getElementById('theme-btn');
const themeIcon = document.getElementById('theme-icon');

// Config
const embedderSelect = document.getElementById('embedder-select');
const chunkerSelect = document.getElementById('chunker-select');
const chunkSizeInput = document.getElementById('chunk-size-input');
const applyConfigBtn = document.getElementById('apply-config-btn');
const statDocs = document.getElementById('stat-docs');
const statChunks = document.getElementById('stat-chunks');

// Toast
const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toast-message');

// Chat
const chatInput = document.getElementById('chat-input');
const sendChatBtn = document.getElementById('send-chat-btn');
const chatHistory = document.getElementById('chat-history');

// Search
const searchQuery = document.getElementById('search-query');
const runSearchBtn = document.getElementById('run-search-btn');
const filterAudience = document.getElementById('filter-audience');
const filterDepartment = document.getElementById('filter-department');
const searchResults = document.getElementById('search-results');

// Documents
const docsList = document.getElementById('docs-list');
const refreshDocsBtn = document.getElementById('refresh-docs-btn');

// Chunking Lab
const sampleText = document.getElementById('sample-text');
const testChunkSize = document.getElementById('test-chunk-size');
const runCompareBtn = document.getElementById('run-compare-btn');
const compareResults = document.getElementById('compare-results');

// --- Global State ---
let isDarkMode = true;

// --- Helper Functions ---
function showToast(message, type = 'info') {
    toastMessage.textContent = message;
    
    // Icon based on type
    let iconName = 'info';
    if (type === 'success') iconName = 'check-circle';
    if (type === 'error') iconName = 'alert-circle';
    
    const iconEl = toast.querySelector('i');
    iconEl.setAttribute('data-lucide', iconName);
    lucide.createIcons();
    
    toast.classList.remove('hide');
    setTimeout(() => {
        toast.classList.add('hide');
    }, 3000);
}

// --- Event Listeners ---

// Navigation
navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        // Update buttons
        navBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // Show target tab
        const targetId = btn.getAttribute('data-target');
        tabContents.forEach(tab => {
            tab.classList.remove('active');
            if (tab.id === targetId) {
                tab.classList.add('active');
            }
        });
    });
});

// Theme Toggle
themeBtn.addEventListener('click', () => {
    isDarkMode = !isDarkMode;
    if (isDarkMode) {
        document.body.classList.remove('light-mode');
        document.body.classList.add('dark-mode');
        themeIcon.setAttribute('data-lucide', 'sun');
    } else {
        document.body.classList.remove('dark-mode');
        document.body.classList.add('light-mode');
        themeIcon.setAttribute('data-lucide', 'moon');
    }
    lucide.createIcons();
});

// Config Panel
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        
        embedderSelect.value = `${data.embedder_type.toUpperCase()} (${data.embedding_model})`;
        chunkerSelect.value = data.chunker_type;
        chunkSizeInput.value = data.chunk_size;
        
        statDocs.textContent = data.document_count;
        statChunks.textContent = data.store_size;
        if (!data.ready) {
            showToast(data.error || 'OpenAI API configuration is not ready', 'error');
        }
    } catch (error) {
        console.error("Failed to load config:", error);
    }
}

applyConfigBtn.addEventListener('click', async () => {
    const originalText = applyConfigBtn.textContent;
    applyConfigBtn.textContent = 'Applying...';
    applyConfigBtn.disabled = true;
    
    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chunker_type: chunkerSelect.value,
                chunk_size: parseInt(chunkSizeInput.value)
            })
        });
        
        const data = await response.json();
        if (!response.ok || !data.ready) {
            throw new Error(data.error || 'OpenAI API configuration failed');
        }
        statDocs.textContent = data.document_count;
        statChunks.textContent = data.store_size;
        
        showToast('Configuration applied successfully', 'success');
    } catch (error) {
        showToast(`Failed to apply configuration: ${error.message}`, 'error');
    } finally {
        applyConfigBtn.textContent = originalText;
        applyConfigBtn.disabled = false;
    }
});

// Chat Functionality
function addMessage(text, isUser = false, sources = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${isUser ? 'user-message' : 'ai-message'} glass-panel fade-in`;
    
    let avatarIcon = isUser ? 'user' : 'bot';
    
    let html = `
        <div class="avatar"><i data-lucide="${avatarIcon}"></i></div>
        <div class="message-content">
            <p>${text.replace(/\n/g, '<br>')}</p>
    `;
    
    if (sources && sources.length > 0) {
        html += `<div class="source-citations">
            <strong>Sources:</strong>
        `;
        
        sources.forEach((source, idx) => {
            const meta = source.metadata || {};
            const sourceName = meta.source || source.id;
            const score = (source.score * 100).toFixed(1) + '%';
            
            html += `
                <div class="source-item" title="${source.content.replace(/"/g, '&quot;')}">
                    <i data-lucide="file-text" class="text-muted" style="width:16px;height:16px;"></i>
                    <div style="flex:1;">
                        <div>[${idx + 1}] ${sourceName.split('/').pop().split('\\').pop()}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">Similarity: ${score}</div>
                    </div>
                </div>
            `;
        });
        
        html += `</div>`;
    }
    
    html += `</div>`;
    msgDiv.innerHTML = html;
    chatHistory.appendChild(msgDiv);
    lucide.createIcons();
    
    // Auto scroll to bottom
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

async function handleChat() {
    const question = chatInput.value.trim();
    if (!question) return;
    
    // Add user message
    addMessage(question, true);
    chatInput.value = '';
    
    // Add loading indicator
    const loadingId = 'loading-' + Date.now();
    const msgDiv = document.createElement('div');
    msgDiv.id = loadingId;
    msgDiv.className = `message ai-message glass-panel fade-in`;
    msgDiv.innerHTML = `
        <div class="avatar"><i data-lucide="bot"></i></div>
        <div class="message-content">
            <div style="display:flex; gap:8px; align-items:center;">
                <i data-lucide="loader" class="animate-spin"></i> Thinking...
            </div>
        </div>
    `;
    chatHistory.appendChild(msgDiv);
    lucide.createIcons();
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, top_k: 3 })
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Chat request failed');
        }
        
        // Remove loading indicator
        document.getElementById(loadingId).remove();
        
        // Add AI response
        addMessage(data.answer, false, data.sources);
    } catch (error) {
        document.getElementById(loadingId).remove();
        addMessage(`Sorry, I encountered an error while processing your request: ${error.message}`, false);
        console.error("Chat error:", error);
    }
}

sendChatBtn.addEventListener('click', handleChat);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleChat();
});

// Search Functionality
runSearchBtn.addEventListener('click', async () => {
    const query = searchQuery.value.trim();
    if (!query) return;
    
    const audience = filterAudience.value.trim();
    const department = filterDepartment.value.trim();
    
    const filter = {};
    if (audience) filter.audience = audience;
    if (department) filter.department = department;
    
    searchResults.innerHTML = `
        <div class="empty-state">
            <i data-lucide="loader" class="animate-spin empty-icon" style="opacity: 1; color: var(--primary);"></i>
            <p>Searching vectors...</p>
        </div>
    `;
    lucide.createIcons();
    
    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, top_k: 5, filter })
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Search request failed');
        }
        
        if (!data.results || data.results.length === 0) {
            searchResults.innerHTML = `
                <div class="empty-state">
                    <i data-lucide="search-x" class="empty-icon"></i>
                    <p>No matches found for your query.</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }
        
        searchResults.innerHTML = '';
        
        data.results.forEach((result, idx) => {
            const meta = result.metadata || {};
            const sourceName = meta.source ? meta.source.split('/').pop().split('\\').pop() : result.id;
            const score = (result.score * 100).toFixed(1) + '%';
            
            let tagsHtml = '';
            for (const [k, v] of Object.entries(meta)) {
                if (k !== 'source' && k !== 'chunk_index' && k !== 'doc_id') {
                    tagsHtml += `<span class="meta-tag">${k}: ${v}</span>`;
                }
            }
            
            const card = document.createElement('div');
            card.className = 'result-card glass-panel fade-in';
            card.style.animationDelay = `${idx * 0.1}s`;
            card.innerHTML = `
                <div class="score-badge">${score} match</div>
                <h3 style="margin-bottom: 8px; font-size: 1.1rem;">${sourceName}</h3>
                <div class="result-meta">
                    <span class="meta-tag"><i data-lucide="hash" style="width:14px;height:14px;"></i> Chunk ${meta.chunk_index !== undefined ? meta.chunk_index : 'N/A'}</span>
                    ${tagsHtml}
                </div>
                <div class="result-content">${result.content}</div>
            `;
            searchResults.appendChild(card);
        });
        lucide.createIcons();
        
    } catch (error) {
        searchResults.innerHTML = `
            <div class="empty-state">
                <i data-lucide="alert-triangle" class="empty-icon" style="color: var(--danger); opacity: 1;"></i>
                <p>An error occurred during search: ${error.message}</p>
            </div>
        `;
        lucide.createIcons();
        console.error("Search error:", error);
    }
});

searchQuery.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') runSearchBtn.click();
});

// Documents Functionality
async function loadDocuments() {
    docsList.innerHTML = `
        <div style="grid-column: 1 / -1; display: flex; justify-content: center; padding: 40px;">
            <i data-lucide="loader" class="animate-spin" style="width: 32px; height: 32px; color: var(--primary);"></i>
        </div>
    `;
    lucide.createIcons();
    
    try {
        const response = await fetch('/api/documents');
        const data = await response.json();
        
        docsList.innerHTML = '';
        
        if (data.documents.length === 0) {
            docsList.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 40px;">
                    No documents found in the database.
                </div>
            `;
            return;
        }
        
        data.documents.forEach((doc, idx) => {
            const meta = doc.metadata || {};
            const title = meta.doc_id || doc.id;
            
            const card = document.createElement('div');
            card.className = 'doc-card glass-panel fade-in';
            card.style.animationDelay = `${idx * 0.05}s`;
            card.innerHTML = `
                <div class="doc-header">
                    <i data-lucide="file-text" class="doc-icon"></i>
                    <div class="doc-title">${title}</div>
                </div>
                <div class="doc-preview">
                    ${doc.content_preview}
                </div>
                <div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:8px;">
                    ${meta.audience ? `<span class="meta-tag text-sm">Audience: ${meta.audience}</span>` : ''}
                    ${meta.department ? `<span class="meta-tag text-sm">Dept: ${meta.department}</span>` : ''}
                </div>
            `;
            docsList.appendChild(card);
        });
        lucide.createIcons();
        
    } catch (error) {
        docsList.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; color: var(--danger); padding: 40px;">
                Error loading documents.
            </div>
        `;
        console.error("Docs error:", error);
    }
}

refreshDocsBtn.addEventListener('click', loadDocuments);

// Chunking Lab Functionality
runCompareBtn.addEventListener('click', async () => {
    const text = sampleText.value.trim();
    if (!text) {
        showToast("Please enter some text to chunk", "error");
        return;
    }
    
    const chunkSize = parseInt(testChunkSize.value) || 200;
    
    const originalText = runCompareBtn.textContent;
    runCompareBtn.textContent = 'Running...';
    runCompareBtn.disabled = true;
    
    try {
        const response = await fetch('/api/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, chunk_size: chunkSize })
        });
        
        const data = await response.json();
        
        compareResults.innerHTML = '';
        compareResults.classList.remove('hide');
        
        const names = {
            'fixed_size': 'Fixed Size',
            'by_sentences': 'Sentence Split',
            'recursive': 'Recursive Split'
        };
        
        for (const [key, result] of Object.entries(data)) {
            const col = document.createElement('div');
            col.className = 'strategy-column';
            
            let chunksHtml = '';
            result.chunks.forEach(c => {
                chunksHtml += `<div class="chunk-block glass-panel">${c.replace(/\n/g, '<br>')}</div>`;
            });
            
            col.innerHTML = `
                <div class="strategy-header">
                    <div style="font-weight: 600;">${names[key] || key}</div>
                    <div class="strategy-stats">
                        ${result.count} chunks • ~${Math.round(result.avg_length)} chars avg
                    </div>
                </div>
                <div class="chunk-list scroll-y" style="max-height: 500px; padding-right: 8px;">
                    ${chunksHtml}
                </div>
            `;
            
            compareResults.appendChild(col);
        }
        
    } catch (error) {
        showToast("Failed to run comparison", "error");
        console.error("Compare error:", error);
    } finally {
        runCompareBtn.textContent = originalText;
        runCompareBtn.disabled = false;
    }
});

// Provide default text for the chunking lab
sampleText.value = `This is a sample document about VinUniversity. VinUni is a private, non-profit university established in Vietnam. 
It aims to be a world-class institution.

The university has several colleges, including the College of Health Sciences, College of Engineering and Computer Science, and College of Business and Management.

Students are expected to adhere to the academic integrity policy. Any form of cheating or plagiarism is strictly prohibited and will result in disciplinary action. The library provides many resources to help students properly cite their sources.`;

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    
    // Add simple spin animation to CSS programmatically for loaders
    const style = document.createElement('style');
    style.textContent = `
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .animate-spin { animation: spin 1s linear infinite; }
    `;
    document.head.appendChild(style);
    
    // Load docs on first load
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.target.classList.contains('active') && mutation.target.id === 'docs-tab') {
                if (docsList.children.length === 0) {
                    loadDocuments();
                }
            }
        });
    });
    
    observer.observe(document.getElementById('docs-tab'), { attributes: true, attributeFilter: ['class'] });
});
