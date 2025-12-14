/**
 * VIDOCQ - Intelligence Autonome
 * Frontend Application Logic
 */

// Configuration
const API_BASE = 'http://localhost:8000';

// State
let isInvestigating = false;
let currentInvestigation = null;

// DOM Elements
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const sidePanel = document.getElementById('side-panel');
const sidePanelContent = document.getElementById('side-panel-content');
const entityCount = document.getElementById('entity-count');
const relationCount = document.getElementById('relation-count');
const connectionStatus = document.getElementById('connection-status');

// Report Modal
const reportModal = document.getElementById('report-modal');
const reportContent = document.getElementById('report-content');
const btnReport = document.getElementById('btn-report');
const btnStats = document.getElementById('btn-stats');


// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    checkServerConnection();
    updateStats();
});

function initEventListeners() {
    // Send button
    sendBtn.addEventListener('click', handleSend);

    // Enter to send
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });

    // Auto-resize textarea
    userInput.addEventListener('input', autoResizeTextarea);

    // Report button
    btnReport.addEventListener('click', generateReport);

    // Stats button
    btnStats.addEventListener('click', () => {
        sidePanel.classList.toggle('open');
        if (sidePanel.classList.contains('open')) {
            loadGraphPreview();
        }
    });

    // Close panel
    document.getElementById('close-panel').addEventListener('click', () => {
        sidePanel.classList.remove('open');
    });

    // Modal controls
    document.getElementById('close-modal').addEventListener('click', closeModal);
    document.getElementById('close-report').addEventListener('click', closeModal);
    document.getElementById('print-report').addEventListener('click', () => window.print());
}

function autoResizeTextarea() {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 150) + 'px';
}


// ============================================
// MESSAGE HANDLING
// ============================================

function handleSend() {
    const message = userInput.value.trim();
    if (!message || isInvestigating) return;

    // Add user message
    addMessage('user', message);

    // Clear input
    userInput.value = '';
    userInput.style.height = 'auto';

    // Start investigation
    startInvestigation(message);
}

function addMessage(type, content, isHtml = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;

    const avatar = type === 'assistant' ? 'V' : 'U';
    const author = type === 'assistant' ? 'Vidocq' : 'Vous';
    const time = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">${author}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-text">
                ${isHtml ? content : `<p>${escapeHtml(content)}</p>`}
            </div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();

    return messageDiv;
}

function addProgressMessage(target) {
    const content = `
        <p>Bien reçu. Je lance l'investigation sur <strong>${escapeHtml(target)}</strong>...</p>
        <div class="investigation-progress" id="progress-container">
            <div class="progress-step active" id="step-profile">
                <span class="icon">⏳</span>
                <span>Profilage de la cible...</span>
            </div>
            <div class="progress-step pending" id="step-queries">
                <span class="icon">○</span>
                <span>Génération des requêtes OSINT...</span>
            </div>
            <div class="progress-step pending" id="step-search">
                <span class="icon">○</span>
                <span>Recherche de sources...</span>
            </div>
            <div class="progress-step pending" id="step-extract">
                <span class="icon">○</span>
                <span>Extraction des entités...</span>
            </div>
            <div class="progress-step pending" id="step-verify">
                <span class="icon">○</span>
                <span>Vérification (Agent Critique)...</span>
            </div>
            <div class="progress-step pending" id="step-complete">
                <span class="icon">○</span>
                <span>Finalisation...</span>
            </div>
        </div>
    `;

    return addMessage('assistant', content, true);
}

function updateProgressStep(stepId, status) {
    const step = document.getElementById(stepId);
    if (!step) return;

    step.className = `progress-step ${status}`;

    const icon = step.querySelector('.icon');
    switch (status) {
        case 'active':
            icon.textContent = '⏳';
            break;
        case 'complete':
            icon.textContent = '✅';
            break;
        case 'error':
            icon.textContent = '❌';
            break;
        default:
            icon.textContent = '○';
    }
}


// ============================================
// INVESTIGATION FLOW
// ============================================

async function startInvestigation(target) {
    isInvestigating = true;
    sendBtn.disabled = true;
    currentInvestigation = target;

    // Add progress message
    const progressMsg = addProgressMessage(target);

    try {
        // Step 1: Preview (Profile + Queries)
        updateProgressStep('step-profile', 'active');
        const preview = await fetchAPI(`/investigate/${encodeURIComponent(target)}/preview`);

        updateProgressStep('step-profile', 'complete');
        updateProgressStep('step-queries', 'active');

        // Small delay for UX
        await delay(500);
        updateProgressStep('step-queries', 'complete');

        // Step 2: Launch actual investigation
        updateProgressStep('step-search', 'active');
        const investigation = await fetchAPI(`/investigate/${encodeURIComponent(target)}`);

        updateProgressStep('step-search', 'complete');
        updateProgressStep('step-extract', 'active');

        // Poll for completion (simplified - in production use WebSocket)
        await delay(2000);
        updateProgressStep('step-extract', 'complete');
        updateProgressStep('step-verify', 'active');

        await delay(1500);
        updateProgressStep('step-verify', 'complete');
        updateProgressStep('step-complete', 'active');

        await delay(500);
        updateProgressStep('step-complete', 'complete');

        // Update stats
        await updateStats();

        // Add completion message
        addCompletionMessage(target, investigation);

    } catch (error) {
        console.error('Investigation error:', error);
        addMessage('assistant', `
            <p>⚠️ Une erreur s'est produite lors de l'investigation.</p>
            <p class="hint">Erreur: ${escapeHtml(error.message)}</p>
            <p>Vérifiez que le serveur backend est en cours d'exécution.</p>
        `, true);
    } finally {
        isInvestigating = false;
        sendBtn.disabled = false;
    }
}

function addCompletionMessage(target, data) {
    const content = `
        <p><strong>Investigation terminée.</strong></p>
        <p>J'ai lancé l'analyse de <strong>${escapeHtml(target)}</strong>. 
        Les résultats sont en cours de traitement par les agents en arrière-plan.</p>
        <div class="message-actions">
            <button class="btn-action" onclick="viewGraph()">🔍 Voir le graphe</button>
            <button class="btn-action primary" onclick="generateReport()">📄 Générer le rapport</button>
        </div>
        <p class="hint" style="margin-top: var(--space-md);">
            💡 Utilisez le bouton 📊 pour voir les statistiques du graphe.
        </p>
    `;

    addMessage('assistant', content, true);
}


// ============================================
// API CALLS
// ============================================

async function fetchAPI(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

async function checkServerConnection() {
    try {
        await fetchAPI('/status');
        connectionStatus.textContent = 'Connecté au serveur';
        document.querySelector('.status-indicator').classList.add('online');
        document.querySelector('.status-indicator').classList.remove('offline');
    } catch (error) {
        connectionStatus.textContent = 'Serveur hors ligne';
        document.querySelector('.status-indicator').classList.remove('online');
        document.querySelector('.status-indicator').classList.add('offline');
    }
}

async function updateStats() {
    try {
        const stats = await fetchAPI('/graph/stats');
        entityCount.textContent = `${stats.entities || 0} entités`;
        relationCount.textContent = `${stats.relationships || 0} relations`;
    } catch (error) {
        console.error('Stats error:', error);
    }
}


// ============================================
// GRAPH & REPORT
// ============================================

function viewGraph() {
    sidePanel.classList.add('open');
    loadGraphPreview();
}

async function loadGraphPreview() {
    sidePanelContent.innerHTML = '<p style="color: var(--text-muted);">Chargement...</p>';

    try {
        const analysis = await fetchAPI('/graph/analyze');

        if (analysis.status === 'empty') {
            sidePanelContent.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📊</span>
                    <p>Aucune donnée dans le graphe.</p>
                    <p>Lancez une investigation pour commencer.</p>
                </div>
            `;
            return;
        }

        // Display report preview
        sidePanelContent.innerHTML = `
            <div style="font-family: var(--font-body); font-size: 14px; line-height: 1.6;">
                <h4 style="margin-bottom: var(--space-md); color: var(--accent-gold);">
                    Statistiques du Graphe
                </h4>
                <p><strong>Entités:</strong> ${analysis.stats?.entity_count || 0}</p>
                <p><strong>Relations:</strong> ${analysis.stats?.relationship_count || 0}</p>
                <hr style="border-color: var(--border-color); margin: var(--space-md) 0;">
                <h4 style="margin-bottom: var(--space-md); color: var(--accent-gold);">
                    Aperçu de l'Analyse
                </h4>
                <div style="white-space: pre-wrap; color: var(--text-secondary); font-size: 13px;">
                    ${escapeHtml(analysis.report?.substring(0, 1000) || 'Analyse non disponible')}...
                </div>
            </div>
        `;
    } catch (error) {
        sidePanelContent.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">⚠️</span>
                <p>Erreur de chargement</p>
                <p style="font-size: 12px;">${escapeHtml(error.message)}</p>
            </div>
        `;
    }
}

async function generateReport() {
    reportModal.classList.add('open');
    reportContent.innerHTML = '<p style="color: var(--text-muted);">Génération du rapport...</p>';

    try {
        const result = await fetchAPI('/report/generate?title=Rapport%20Vidocq');

        if (result.status === 'success') {
            // Fetch and display HTML report
            const htmlResponse = await fetch(`${API_BASE}/report/view?path=${result.html_path}`);
            const htmlContent = await htmlResponse.text();

            reportContent.innerHTML = `
                <iframe 
                    srcdoc="${escapeHtml(htmlContent)}" 
                    style="width: 100%; height: 60vh; border: 1px solid var(--border-color); border-radius: 8px;"
                ></iframe>
            `;
        }
    } catch (error) {
        reportContent.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">⚠️</span>
                <p>Erreur de génération</p>
                <p style="font-size: 12px;">${escapeHtml(error.message)}</p>
            </div>
        `;
    }
}

function closeModal() {
    reportModal.classList.remove('open');
}


// ============================================
// UTILITIES
// ============================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


// ============================================
// EXPOSE GLOBAL FUNCTIONS FOR ONCLICK
// ============================================

window.viewGraph = viewGraph;
window.generateReport = generateReport;
