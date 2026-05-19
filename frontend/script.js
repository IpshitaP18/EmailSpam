const API_URL = 'http://localhost:5000';

const samples = [
    "Congratulations! You have won a free iPhone! Click here to claim your prize now!",
    "Hi, I wanted to follow up on our meeting tomorrow at 2 PM. Can you confirm your availability?",
    "URGENT! Your bank account has been compromised. Click here to verify your password immediately.",
    "Your order has been shipped and will arrive in 2-3 business days. Thank you for your purchase!"
];

// Statistics
let stats = {
    total: 0,
    spam: 0,
    legitimate: 0
};

// DOM Elements - Email Classification
const emailText = document.getElementById('emailText');
const classifyBtn = document.getElementById('classifyBtn');
const clearBtn = document.getElementById('clearBtn');
const resultContainer = document.getElementById('resultContainer');
const resultBox = document.getElementById('resultBox');
const confidenceChart = document.getElementById('confidenceChart');
const loadingSpinner = document.getElementById('loadingSpinner');

// DOM Elements - Batch
const batchEmails = document.getElementById('batchEmails');
const batchClassifyBtn = document.getElementById('batchClassifyBtn');
const clearBatchBtn = document.getElementById('clearBatchBtn');
const batchResultContainer = document.getElementById('batchResultContainer');
const batchStats = document.getElementById('batchStats');
const batchResults = document.getElementById('batchResults');
const batchLoadingSpinner = document.getElementById('batchLoadingSpinner');

// Gmail Integration Elements
const gmailConnectBtn = document.getElementById('gmailConnectBtn');
const gmailSettingsBtn = document.getElementById('gmailSettingsBtn');
const gmailStatsBtn = document.getElementById('gmailStatsBtn');
const gmailRefreshStatusBtn = document.getElementById('gmailRefreshStatusBtn');
const gmailStatus = document.getElementById('gmailStatus');
const gmailConnectionStatus = document.getElementById('gmailConnectionStatus');
const gmailScanStatus = document.getElementById('gmailScanStatus');
const gmailRecentScans = document.getElementById('gmailRecentScans');
const statsContainer = document.getElementById('statsContainer');

// Event Listeners
classifyBtn.addEventListener('click', classifyEmail);
clearBtn.addEventListener('click', () => {
    emailText.value = '';
    resultContainer.classList.add('hidden');
});

batchClassifyBtn.addEventListener('click', classifyBatch);
clearBatchBtn.addEventListener('click', () => {
    batchEmails.value = '';
    batchResultContainer.classList.add('hidden');
});

// Gmail Integration Listeners
gmailConnectBtn.addEventListener('click', connectGmail);
gmailSettingsBtn.addEventListener('click', configureGmailBot);
gmailStatsBtn.addEventListener('click', viewGmailStats);
if (gmailRefreshStatusBtn) {
    gmailRefreshStatusBtn.addEventListener('click', async () => {
        gmailRefreshStatusBtn.disabled = true;
        await checkGmailConnection();
        gmailRefreshStatusBtn.disabled = false;
    });
}

// Initialize on page load
window.addEventListener('load', async () => {
    loadModelInfo();
    updateStatistics();
    await checkGmailConnection();
    setInterval(checkGmailConnection, 15000);
});

// ==================== GMAIL STATUS FUNCTIONS ====================

async function checkGmailConnection() {
    if (!gmailConnectionStatus) return;

    try {
        const response = await fetch(`${API_URL}/api/gmail-status`);
        if (!response.ok) {
            throw new Error('Unable to fetch Gmail connection status');
        }

        const data = await response.json();
        updateGmailConnectionStatus(data);
        updateGmailScanStatus(data.scan_status || {});
        updateRecentScans(data.recent_scans || []);
    } catch (error) {
        updateGmailConnectionStatus({
            connected: false,
            message: 'Backend is unavailable. Start the backend server on http://localhost:5000.',
            account: null
        });
        updateGmailScanStatus({
            state: 'error',
            message: 'Backend unavailable. Gmail scan status cannot be fetched.',
            processed: 0,
            total: 0,
            last_email: null
        });
    }
}

function updateGmailConnectionStatus(data) {
    if (!gmailConnectionStatus) return;

    gmailConnectionStatus.classList.toggle('connected', Boolean(data.connected));
    gmailConnectionStatus.classList.toggle('disconnected', !Boolean(data.connected));
    gmailConnectionStatus.textContent = data.connected
        ? `Connected as ${data.account || 'Gmail user'}`
        : 'Gmail Disconnected';
    gmailConnectionStatus.title = data.message || '';
}

function updateGmailScanStatus(scan) {
    if (!gmailScanStatus) return;

    const isActive = scan.state === 'scanning';
    gmailScanStatus.classList.toggle('connected', isActive);
    gmailScanStatus.classList.toggle('disconnected', !isActive);

    if (scan.state === 'scanning') {
        gmailScanStatus.textContent = `Scanning ${scan.processed}/${scan.total} — ${scan.last_email || '...'}`;
    } else if (scan.state === 'completed') {
        gmailScanStatus.textContent = `Last scan complete: ${scan.processed}/${scan.total}`;
    } else if (scan.state === 'error') {
        gmailScanStatus.textContent = scan.message || 'Backend unavailable';
    } else {
        gmailScanStatus.textContent = scan.message || 'Scan idle';
    }

    gmailScanStatus.title = scan.message || '';
}

function updateRecentScans(recent) {
    if (!gmailRecentScans) return;

    if (!Array.isArray(recent) || recent.length === 0) {
        gmailRecentScans.classList.add('hidden');
        gmailRecentScans.innerHTML = '';
        return;
    }

    gmailRecentScans.classList.remove('hidden');
    let html = '<h4>Recent Scanned Emails</h4>';
    html += '<div class="recent-list">';
    recent.slice(0,10).forEach(item => {
        html += `<div class="recent-item ${item.is_spam ? 'spam' : 'legit'}">
            <div class="recent-row">
                <div class="recent-subject">${escapeHtml(item.subject || '')}</div>
                <div class="recent-label">${item.label} — ${(item.spam_confidence*100 || 0).toFixed(1)}% </div>
            </div>
            <div class="recent-meta">From: ${escapeHtml(item.sender || '')} • ${new Date(item.timestamp).toLocaleString()}</div>
            <div class="recent-reasoning">${renderReasoning(item.reasoning || [])}</div>
        </div>`;
    });
    html += '</div>';
    gmailRecentScans.innerHTML = html;
}

function renderReasoning(reasoning) {
    if (!Array.isArray(reasoning) || reasoning.length === 0) return '';
    let parts = reasoning.map(r => `<span class="reason-term">${escapeHtml(r.term)}</span>`);
    return `<div class="reasoning-label">Top terms:</div><div class="reason-list">${parts.join(' ')}</div>`;
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// ==================== CLASSIFICATION FUNCTIONS ====================

async function classifyEmail() {
    const text = emailText.value.trim();

    if (!text) {
        showAlert('Please enter email content', 'error');
        return;
    }

    if (text.length < 5) {
        showAlert('Email content must be at least 5 characters long', 'error');
        return;
    }

    loadingSpinner.classList.remove('hidden');
    classifyBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/api/classify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email_text: text })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Classification failed');
        }

        const result = await response.json();
        displayResult(result);
        resultContainer.classList.remove('hidden');
        
        // Update stats
        stats.total++;
        if (result.is_spam) stats.spam++;
        else stats.legitimate++;
        updateStatistics();
    } catch (error) {
        showAlert(`Error: ${error.message}`, 'error');
        resultContainer.classList.add('hidden');
    } finally {
        loadingSpinner.classList.add('hidden');
        classifyBtn.disabled = false;
    }
}

async function classifyBatch() {
    const text = batchEmails.value.trim();

    if (!text) {
        showAlert('Please enter email content', 'error');
        return;
    }

    const emailList = text.split(/\n\n+/).filter(e => e.trim().length >= 5);

    if (emailList.length === 0) {
        showAlert('No valid emails found. Each email must be at least 5 characters long.', 'error');
        return;
    }

    batchLoadingSpinner.classList.remove('hidden');
    batchClassifyBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/api/batch-classify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ emails: emailList })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Batch classification failed');
        }

        const data = await response.json();
        displayBatchResults(data.results, emailList);
        batchResultContainer.classList.remove('hidden');
        
        // Update stats
        data.results.forEach(result => {
            stats.total++;
            if (result.is_spam) stats.spam++;
            else stats.legitimate++;
        });
        updateStatistics();
    } catch (error) {
        showAlert(`Error: ${error.message}`, 'error');
        batchResultContainer.classList.add('hidden');
    } finally {
        batchLoadingSpinner.classList.add('hidden');
        batchClassifyBtn.disabled = false;
    }
}

// ==================== DISPLAY FUNCTIONS ====================

function displayResult(result) {
    const isSpam = result.is_spam;
    const spamConfidence = (result.spam_confidence * 100).toFixed(2);
    const legitConfidence = (result.legitimate_confidence * 100).toFixed(2);

    resultBox.className = `result-box ${isSpam ? 'result-spam' : 'result-legitimate'}`;
    resultBox.innerHTML = `
        <div style="font-size: 1.3em; margin-bottom: 10px;">
            ${isSpam ? '⚠️ SPAM DETECTED' : '✅ LEGITIMATE'}
        </div>
        <div style="font-size: 0.95em;">
            Classification: ${result.label}
        </div>
    `;

    confidenceChart.innerHTML = `
        <div class="confidence-item">
            <div class="confidence-label">🚨 Spam Confidence</div>
            <div class="confidence-bar">
                <div class="confidence-fill spam-fill" style="width: ${spamConfidence}%">
                    ${spamConfidence}%
                </div>
            </div>
        </div>
        <div class="confidence-item">
            <div class="confidence-label">✅ Legitimate Confidence</div>
            <div class="confidence-bar">
                <div class="confidence-fill legitimate-fill" style="width: ${legitConfidence}%">
                    ${legitConfidence}%
                </div>
            </div>
        </div>
    `;
}

function displayBatchResults(results, emailList) {
    const spamCount = results.filter(r => r.is_spam).length;
    const legitCount = results.filter(r => !r.is_spam).length;

    batchStats.innerHTML = `
        <div class="stat-card">
            <h4>Total Emails</h4>
            <div class="stat-value">${results.length}</div>
        </div>
        <div class="stat-card">
            <h4>🚨 Spam</h4>
            <div class="stat-value" style="color: #ffc107;">${spamCount}</div>
        </div>
        <div class="stat-card">
            <h4>✅ Legitimate</h4>
            <div class="stat-value" style="color: #66bb6a;">${legitCount}</div>
        </div>
        <div class="stat-card">
            <h4>Spam Rate</h4>
            <div class="stat-value">${((spamCount / results.length) * 100).toFixed(1)}%</div>
        </div>
    `;

    let resultsHTML = '';
    results.forEach((result, index) => {
        const email = emailList[index];
        const isSpam = result.is_spam;
        const confidence = isSpam ? result.spam_confidence : result.legitimate_confidence;

        resultsHTML += `
            <div class="batch-result-item ${isSpam ? 'spam' : 'legitimate'}">
                <div class="batch-result-text">
                    <strong>Email ${index + 1}:</strong> ${email.substring(0, 100)}${email.length > 100 ? '...' : ''}
                </div>
                <span class="batch-result-label ${isSpam ? 'spam' : 'legitimate'}">
                    ${isSpam ? '🚨 SPAM' : '✅ LEGITIMATE'} (${(confidence * 100).toFixed(1)}% confidence)
                </span>
            </div>
        `;
    });

    batchResults.innerHTML = resultsHTML;
}

function updateStatistics() {
    const spamRate = stats.total > 0 ? ((stats.spam / stats.total) * 100).toFixed(1) : 0;
    
    statsContainer.innerHTML = `
        <div class="stat-card">
            <h4>Total Classified</h4>
            <div class="stat-value">${stats.total}</div>
        </div>
        <div class="stat-card">
            <h4>🚨 Spam Detected</h4>
            <div class="stat-value">${stats.spam}</div>
        </div>
        <div class="stat-card">
            <h4>✅ Legitimate</h4>
            <div class="stat-value">${stats.legitimate}</div>
        </div>
        <div class="stat-card">
            <h4>Spam Rate</h4>
            <div class="stat-value">${spamRate}%</div>
        </div>
    `;
}

// ==================== GMAIL INTEGRATION FUNCTIONS ====================

async function connectGmail() {
    gmailStatus.classList.remove('hidden');
    gmailStatus.innerHTML = `
        <div class="alert alert-warning">
            <h3>🔗 Gmail Integration Setup</h3>
            <p><strong>Step 1:</strong> Create a Google Cloud Project</p>
            <ol style="margin: 10px 0; padding-left: 20px;">
                <li>Go to <a href="https://console.cloud.google.com" target="_blank">Google Cloud Console</a></li>
                <li>Create a new project called "SpamGuard Bot"</li>
                <li>Enable Gmail API</li>
                <li>Create OAuth 2.0 credentials (Desktop application)</li>
                <li>Download the credentials JSON file</li>
            </ol>
            <p><strong>Step 2:</strong> Install Gmail backend module</p>
            <pre style="background: #f0f7ff; padding: 10px; margin: 10px 0; border-radius: 5px; overflow-x: auto;">pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client</pre>
            <p><strong>Step 3:</strong> Run the Gmail bot</p>
            <pre style="background: #f0f7ff; padding: 10px; margin: 10px 0; border-radius: 5px; overflow-x: auto;">python gmail_bot.py</pre>
            <p class="alert alert-success" style="margin-top: 15px;">✅ Instructions saved! See GMAIL_SETUP.md for detailed setup guide.</p>
        </div>
    `;
    showAlert('Gmail setup instructions displayed. See the section below.', 'warning');
    await checkGmailConnection();
}

async function configureGmailBot() {
    gmailStatus.classList.remove('hidden');
    gmailStatus.innerHTML = `
        <div class="alert alert-warning">
            <h3>⚙️ Gmail Bot Configuration</h3>
            <p><strong>Available Settings:</strong></p>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li><strong>Auto-filter:</strong> Automatically move spam to Spam folder</li>
                <li><strong>Scheduled scans:</strong> Set scan frequency (hourly, daily, weekly)</li>
                <li><strong>Label spam:</strong> Add custom labels to detected spam</li>
                <li><strong>Notifications:</strong> Get alerts for high-confidence spam</li>
                <li><strong>Whitelist:</strong> Add trusted senders to whitelist</li>
                <li><strong>Archive legitimate:</strong> Auto-archive clean emails</li>
            </ul>
            <p style="margin-top: 15px; color: #666;">Configuration will be saved in <code>gmail_config.json</code></p>
        </div>
    `;
    showAlert('Bot configuration options displayed', 'warning');
}

async function viewGmailStats() {
    gmailStatus.classList.remove('hidden');
    gmailStatus.innerHTML = `<div class="alert alert-info"><h3>📊 Gmail Bot Statistics</h3><p>Loading live statistics...</p></div>`;

    try {
        const resp = await fetch(`${API_URL}/api/gmail-history?limit=200`);
        if (!resp.ok) throw new Error('No history');
        const data = await resp.json();
        const history = Array.isArray(data.history) ? data.history : [];

        // Compute simple stats
        const total = history.length;
        const spamCount = history.filter(h => h.is_spam).length;
        const legitCount = total - spamCount;
        const avgConfidence = history.length > 0 ? (history.reduce((s, h) => s + (h.spam_confidence || 0), 0) / history.length) * 100 : 0;
        const moved = history.filter(h => h.is_spam && h.moved).length || 0;

        gmailStatus.innerHTML = `
            <div class="alert alert-success">
                <h3>📊 Gmail Bot Statistics</h3>
                <p><strong>Connected:</strong> ${gmailConnectionStatus.textContent || 'Unknown'}</p>
                <div style="display:flex; gap:12px; flex-wrap:wrap; margin-top:10px;">
                    <div class="stat-card"><h4>Emails scanned</h4><div class="stat-value">${total}</div></div>
                    <div class="stat-card"><h4>🚨 Spam detected</h4><div class="stat-value">${spamCount}</div></div>
                    <div class="stat-card"><h4>✅ Legitimate</h4><div class="stat-value">${legitCount}</div></div>
                    <div class="stat-card"><h4>Avg. Spam Confidence</h4><div class="stat-value">${avgConfidence.toFixed(1)}%</div></div>
                    <div class="stat-card"><h4>Moved to Spam</h4><div class="stat-value">${moved}</div></div>
                </div>
                <p style="margin-top:12px; color:#555;">Showing recent ${Math.min(200, total)} scan entries from history.</p>
            </div>
        `;

        // Also update recent scans panel
        updateRecentScans(history.slice(0, 10));
        showAlert('Live Gmail bot statistics loaded', 'success');
    } catch (err) {
        gmailStatus.innerHTML = `
            <div class="alert alert-warning">
                <h3>📊 Gmail Bot Statistics</h3>
                <p>Unable to load live statistics. Ensure the backend and Gmail bot are running.</p>
            </div>
        `;
        showAlert('Could not load Gmail bot statistics', 'warning');
    }
}

// ==================== UTILITY FUNCTIONS ====================

async function loadModelInfo() {
    try {
        const response = await fetch(`${API_URL}/api/model-info`);
        const data = await response.json();

        const modelInfoDiv = document.getElementById('modelInfo');
        modelInfoDiv.innerHTML = `
            <p><strong>🤖 Model Type:</strong> ${data.model_type}</p>
            <p><strong>📦 Version:</strong> ${data.version}</p>
            <p><strong>📝 Description:</strong> ${data.description}</p>
            <p><strong>⭐ Performance:</strong> ${data.accuracy}</p>
            <p><strong>🟢 Status:</strong> ${data.model_ready ? 'Ready' : 'Loading...'}</p>
        `;
    } catch (error) {
        const modelInfoDiv = document.getElementById('modelInfo');
        modelInfoDiv.innerHTML = `
            <div class="alert alert-warning">
                Could not load model information. Make sure the backend server is running on port 5000.
            </div>
        `;
    }
}

function loadSample(index) {
    emailText.value = samples[index];
    emailText.focus();
}

function showAlert(message, type = 'error') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;

    const main = document.querySelector('main');
    main.insertBefore(alertDiv, main.firstChild);

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

async function checkBackendAvailability() {
    try {
        const response = await fetch(`${API_URL}/`, {
            method: 'GET',
            mode: 'cors'
        });
        return response.ok;
    } catch (error) {
        return false;
    }
}

window.addEventListener('load', async () => {
    const isAvailable = await checkBackendAvailability();
    if (!isAvailable) {
        showAlert(
            'Warning: Backend server is not running. Please start it at http://localhost:5000',
            'warning'
        );
    }
});
