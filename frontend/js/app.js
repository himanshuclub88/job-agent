document.addEventListener('DOMContentLoaded', () => {
    /* --- State & Config --- */
    const API_URL = "http://127.0.0.1:8000/api/summary";
    const API_RUN_PIPELINE = "http://127.0.0.1:8000/api/run-pipeline";
    const API_PIPELINE_STATUS = "http://127.0.0.1:8000/api/pipeline-status";
    
    // Pipeline state
    let isPipelineRunning = false;
    let pipelineStartTime = 0;
    let localProgressTimer = null;
    let serverPollTimer = null;
    let lastRenderedLogCount = 0;

    // Filter & Search State
    let currentFilter = 'all';
    let currentSearch = '';
    let globalData = null;

    // Fallback Data
    const fallbackData = {
        "last_run": "29 Sep 2026, 05:15 PM",
        "last_run_duration": "4 minutes, 20 seconds",
        "responsibilities": [],
        "opportunities": [],
        "updates": [],
        "upcoming": [],
        "dont_miss": []
    };

    /* --- Initialization --- */
    function init() {
        const today = new Date();
        const formattedDate = today.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
        
        document.getElementById('current-date').textContent = formattedDate;
        document.getElementById('pipeline-date-display').textContent = formattedDate; 

        loadSettings();
        fetchData();
        setupEvents();
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        document.getElementById('theme-select').value = theme;
        localStorage.setItem('theme', theme);
        
        document.querySelectorAll('.theme-dot').forEach(dot => {
            if (dot.getAttribute('data-theme-val') === theme) {
                dot.classList.add('active');
            } else {
                dot.classList.remove('active');
            }
        });
    }

    function loadSettings() {
        const theme = localStorage.getItem('theme') || 'light';
        const textSize = localStorage.getItem('textSize') || 'text-md';
        
        applyTheme(theme);
        document.body.className = textSize;
        document.getElementById('text-size-select').value = textSize;
    }

    function formatReceivedDate(isoStr) {
        if (!isoStr) return "";
        try {
            const d = new Date(isoStr);
            if (isNaN(d.getTime())) return isoStr;
            const now = new Date();
            const diffHours = Math.round((now - d) / (1000 * 60 * 60));
            if (diffHours >= 0 && diffHours < 24) {
                return `${diffHours === 0 ? 'Just now' : diffHours + 'h ago'}`;
            }
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        } catch(e) {
            return isoStr;
        }
    }

    /* --- DOM Events --- */
    function setupEvents() {
        const notifBtn = document.getElementById('notif-btn');
        const notifDropdown = document.getElementById('notif-dropdown');
        notifBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            notifDropdown.classList.toggle('hidden');
        });
        document.addEventListener('click', (e) => {
            if (!document.getElementById('notif-wrapper').contains(e.target)) {
                notifDropdown.classList.add('hidden');
            }
        });

        document.getElementById('dashboard-search').addEventListener('input', (e) => {
            currentSearch = e.target.value.toLowerCase().trim();
            filterAndRender();
        });

        document.querySelectorAll('.filter-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                currentFilter = chip.getAttribute('data-filter');
                filterAndRender();
            });
        });

        document.getElementById('nav-settings').addEventListener('click', (e) => {
            e.preventDefault();
            openModal('settings-modal');
        });
        document.getElementById('close-settings-btn').addEventListener('click', () => closeModal('settings-modal'));
        
        document.getElementById('theme-select').addEventListener('change', (e) => applyTheme(e.target.value));
        document.querySelectorAll('.theme-dot').forEach(dot => {
            dot.addEventListener('click', (e) => applyTheme(e.target.getAttribute('data-theme-val')));
        });
        document.getElementById('text-size-select').addEventListener('change', (e) => {
            document.body.className = e.target.value;
            localStorage.setItem('textSize', e.target.value);
        });

        document.getElementById('nav-run-pipeline').addEventListener('click', (e) => {
            e.preventDefault();
            openModal('pipeline-modal');
            if (isPipelineRunning) {
                document.getElementById('pipeline-config-view').classList.add('hidden');
                document.getElementById('pipeline-progress-view').classList.remove('hidden');
            } else {
                document.getElementById('pipeline-config-view').classList.remove('hidden');
                document.getElementById('pipeline-progress-view').classList.add('hidden');
                
                if (globalData) {
                    document.getElementById('last-run-time-val').textContent = globalData.last_run || "Not recorded yet";
                    document.getElementById('last-run-duration-val').textContent = globalData.last_run_duration || "--";
                }
                
                document.getElementById('progress-spinner').classList.remove('hidden');
                document.getElementById('progress-success').classList.add('hidden');
                document.getElementById('completion-stats').classList.add('hidden');
                document.getElementById('pipeline-done-actions').classList.add('hidden');
                document.getElementById('progress-status-text').textContent = "Extracting emails & analyzing data...";
                document.getElementById('progress-subtext').classList.remove('hidden');
                document.getElementById('progress-fill').style.width = '0%';
                document.getElementById('progress-fill').classList.add('gradient-bar');
                document.getElementById('progress-percentage').textContent = '0%';
                document.getElementById('progress-percentage').style.color = 'var(--primary)';
                document.getElementById('progress-time').textContent = '0:00';
            }
        });
        
        document.getElementById('close-pipeline-btn').addEventListener('click', () => closeModal('pipeline-modal'));
        document.getElementById('done-pipeline-btn').addEventListener('click', () => closeModal('pipeline-modal'));
        
        document.getElementById('modal-overlay').addEventListener('click', () => {
            closeModal('pipeline-modal');
            closeModal('settings-modal');
        });

        document.getElementById('start-pipeline-btn').addEventListener('click', startPipeline);
    }

    /* --- Data Fetching & Filter Logic --- */
    async function fetchData() {
        try {
            const res = await fetch(API_URL);
            if (!res.ok) throw new Error("API not accessible");
            globalData = await res.json();
            filterAndRender();
        } catch (err) {
            globalData = fallbackData;
            filterAndRender();
        }
    }

    function itemMatches(item) {
        if (currentSearch) {
            const combinedText = `
                ${item.company || ''} 
                ${item.job_title || ''} 
                ${item.text || ''} 
                ${item.recruiter || ''} 
                ${item.location || ''}
            `.toLowerCase();
            if (!combinedText.includes(currentSearch)) {
                return false;
            }
        }

        if (currentFilter === 'all') return true;
        const haystack = `${item.company || ''} ${item.job_title || ''} ${item.text || ''} ${item.location || ''}`.toLowerCase();
        
        if (currentFilter === 'ai') return haystack.includes('ai') || haystack.includes('genai') || haystack.includes('gpt');
        if (currentFilter === 'data') return haystack.includes('data') || haystack.includes('pyspark') || haystack.includes('spark') || haystack.includes('sql');
        if (currentFilter === 'remote') return haystack.includes('remote');
        if (currentFilter === 'action') return haystack.includes('dm') || haystack.includes('contact') || haystack.includes('resume') || haystack.includes('apply');
        return true;
    }

    function filterAndRender() {
        if (!globalData) return;

        if (globalData.dont_miss && globalData.dont_miss.length > 0) {
            document.getElementById('notif-badge').textContent = globalData.dont_miss.length;
            document.getElementById('notif-list').innerHTML = globalData.dont_miss.map(alert => `
                <div class="notif-item">
                    <i class="fa-solid fa-circle-exclamation"></i>
                    <div>${alert}</div>
                </div>
            `).join('');
        } else {
            document.getElementById('notif-list').innerHTML = '<div style="padding:15px;text-align:center;color:var(--text-muted);">All caught up!</div>';
        }

        const filteredResponsibilities = (globalData.responsibilities || []).filter(itemMatches);
        const filteredOpportunities = (globalData.opportunities || []).filter(itemMatches);
        const filteredUpdates = (globalData.updates || []).filter(itemMatches);
        const filteredUpcoming = (globalData.upcoming || []).filter(itemMatches);

        renderRows('responsibilities-list', 'resp-count', filteredResponsibilities, item => {
            const emailUrl = `https://mail.google.com/mail/u/1/#all/${item.thread_id}`;
            const receivedText = formatReceivedDate(item.received_at);
            
            return `
            <div class="list-item">
                <div class="item-content">
                    <div class="item-title">${item.job_title ? item.job_title : item.company || 'Unknown'}</div>
                    <div class="item-desc">${item.text}</div>
                    <div class="item-badges">
                        ${receivedText ? `<span class="pill received-pill"><i class="fa-regular fa-clock"></i> Recv ${receivedText}</span>` : ''}
                        ${item.company && item.job_title ? `<span class="pill">${item.company}</span>` : ''}
                        ${item.recruiter ? `<span class="pill"><i class="fa-regular fa-user"></i> ${item.recruiter}</span>` : ''}
                    </div>
                </div>
                <div class="item-actions">
                    <a href="${emailUrl}" target="_blank" class="btn btn-outline btn-sm"><i class="fa-regular fa-envelope"></i> Email</a>
                </div>
            </div>`;
        });

        renderRows('opportunities-list', 'opp-count', filteredOpportunities, item => {
            const emailUrl = `https://mail.google.com/mail/u/1/#all/${item.thread_id}`;
            const receivedText = formatReceivedDate(item.received_at);
            return `
            <div class="list-item">
                <div class="item-content">
                    <div class="item-title">${item.job_title || 'Role Unspecified'}</div>
                    <div class="item-desc">${item.company || 'Unknown Company'}</div>
                    <div class="item-badges">
                        ${receivedText ? `<span class="pill received-pill"><i class="fa-regular fa-clock"></i> Recv ${receivedText}</span>` : ''}
                        ${item.location ? `<span class="pill"><i class="fa-solid fa-location-dot"></i> ${item.location}</span>` : ''}
                        ${item.source ? `<span class="pill">${item.source}</span>` : ''}
                    </div>
                </div>
                <div class="item-actions">
                    ${item.url ? `<a href="${item.url}" target="_blank" class="btn btn-primary btn-sm">Apply</a>` : ''}
                    <a href="${emailUrl}" target="_blank" class="btn btn-outline btn-sm">Email</a>
                </div>
            </div>`;
        });

        renderRows('updates-list', 'update-count', filteredUpdates, item => {
            const receivedText = formatReceivedDate(item.received_at);
            return `
            <div class="feed-item">
                <div class="feed-meta">
                    <span><i class="fa-solid fa-circle-check" style="margin-right: 4px;"></i> Update</span>
                    ${receivedText ? `<span style="margin-left:auto; font-weight:normal; font-size:0.9em; color:var(--text-muted);">${receivedText}</span>` : ''}
                </div>
                <div class="feed-title">${item.text}</div>
                <a href="https://mail.google.com/mail/u/1/#all/${item.thread_id}" target="_blank" class="text-muted" style="font-size:0.85em;"><i class="fa-solid fa-arrow-right"></i> View Source</a>
            </div>`;
        });

        renderRows('upcoming-list', 'upc-count', filteredUpcoming, item => {
            const receivedText = formatReceivedDate(item.received_at);
            return `
            <div class="feed-item">
                <div class="feed-meta" style="color: var(--warning);">
                    <span><i class="fa-regular fa-clock" style="margin-right: 4px;"></i> ${item.date || ''} ${item.time ? 'at ' + item.time : ''}</span>
                    ${receivedText ? `<span style="margin-left:auto; font-weight:normal; font-size:0.9em; color:var(--text-muted);">${receivedText}</span>` : ''}
                </div>
                <div class="feed-title">${item.text}</div>
                ${item.link ? `<a href="${item.link}" target="_blank" class="text-muted" style="font-size:0.85em;"><i class="fa-solid fa-link"></i> External Link</a>` : ''}
            </div>`;
        });
    }

    function renderRows(containerId, countId, items, templateFn) {
        const container = document.getElementById(containerId);
        const count = document.getElementById(countId);
        
        if (!items || items.length === 0) {
            container.innerHTML = '<div style="padding:32px;text-align:center;color:var(--text-muted); font-size:0.9em;">No matching items found.</div>';
            count.textContent = '0';
            return;
        }
        count.textContent = items.length;
        container.innerHTML = items.map(templateFn).join('');
    }


    /* --- Modal & Pipeline Logic --- */
    function openModal(id) {
        document.getElementById('modal-overlay').classList.remove('hidden');
        document.getElementById(id).classList.remove('hidden');
    }
    
    function closeModal(id) {
        document.getElementById('modal-overlay').classList.add('hidden');
        document.getElementById(id).classList.add('hidden');
    }

    function appendTerminalLog(msg, stepBadge = null) {
        const terminal = document.getElementById('terminal-body');
        const line = document.createElement('div');
        line.className = 'terminal-line';
        line.textContent = `> ${msg}`;
        terminal.appendChild(line);
        terminal.scrollTop = terminal.scrollHeight;
        
        if (stepBadge) {
            document.getElementById('terminal-step-badge').textContent = stepBadge;
        }
    }

    async function startPipeline() {
        const startBtn = document.getElementById('start-pipeline-btn');
        startBtn.disabled = true;

        document.getElementById('pipeline-config-view').classList.add('hidden');
        document.getElementById('pipeline-progress-view').classList.remove('hidden');
        
        isPipelineRunning = true;
        pipelineStartTime = Date.now();
        lastRenderedLogCount = 0;

        document.getElementById('terminal-body').innerHTML = '';
        appendTerminalLog("Initializing connection to backend API...", "Init");

        try {
            const res = await fetch(API_RUN_PIPELINE, { method: 'POST' });
            if (!res.ok) {
                appendTerminalLog(`Backend error: HTTP ${res.status}`, "Error");
            } else {
                appendTerminalLog("Backend acknowledged. Background task started.", "Phase 1");
            }
        } catch(e) {
            appendTerminalLog(`Network Error: Cannot reach API at ${API_RUN_PIPELINE}`, "Failed");
            appendTerminalLog("Ensure 'python server.py' is running.", "Info");
        }
        
        localProgressTimer = setInterval(updateVisualProgress, 1000);
        serverPollTimer = setInterval(pollServerStatus, 1500);
    }

    function formatTime(seconds) {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return m + ":" + (s < 10 ? "0" : "") + s;
    }

    function updateVisualProgress() {
        if (!isPipelineRunning) return;
        
        const elapsedSec = (Date.now() - pipelineStartTime) / 1000;
        let p = 0;

        if (elapsedSec < 600) {
            p = (elapsedSec / 600) * 90;
        } else {
            let extraMin = (elapsedSec - 600) / 60;
            p = 90 + extraMin;
            if (p > 99) p = 99;
        }

        document.getElementById('progress-fill').style.width = p + '%';
        document.getElementById('progress-percentage').textContent = Math.floor(p) + '%';
        document.getElementById('progress-time').textContent = formatTime(elapsedSec);
    }

    async function pollServerStatus() {
        if (!isPipelineRunning) return;
        
        try {
            const res = await fetch(API_PIPELINE_STATUS);
            if (res.ok) {
                const status = await res.json();
                
                if (status.logs && status.logs.length > lastRenderedLogCount) {
                    const newLogs = status.logs.slice(lastRenderedLogCount);
                    newLogs.forEach(logLine => {
                        appendTerminalLog(logLine, status.current_step);
                    });
                    lastRenderedLogCount = status.logs.length;
                }

                if (status.is_running === false) {
                    if (status.duration_str && status.duration_str !== "Failed") {
                        finishPipeline(status.duration_str, status.message);
                    } else {
                        appendTerminalLog(`Pipeline terminated: ${status.message}`, "Failed");
                        finishPipeline("0:00", "Pipeline failed or stopped.");
                    }
                }
            }
        } catch (e) {
            // Ignore temporary network drops
        }
    }

    function finishPipeline(durationStr, messageOverride = null) {
        clearInterval(localProgressTimer);
        clearInterval(serverPollTimer);
        
        isPipelineRunning = false;
        document.getElementById('start-pipeline-btn').disabled = false;

        const fillBar = document.getElementById('progress-fill');
        fillBar.style.width = '100%';
        fillBar.classList.remove('gradient-bar');
        fillBar.style.background = 'var(--success)';
        
        const percentageTxt = document.getElementById('progress-percentage');
        percentageTxt.textContent = '100%';
        percentageTxt.style.color = 'var(--success)';
        
        document.getElementById('progress-spinner').classList.add('hidden');
        document.getElementById('progress-success').classList.remove('hidden');
        document.getElementById('progress-status-text').textContent = messageOverride || "Pipeline processing complete!";
        document.getElementById('progress-subtext').classList.add('hidden');
        
        const statsPanel = document.getElementById('completion-stats');
        statsPanel.classList.remove('hidden');
        document.getElementById('final-duration-text').textContent = `Task completed in ${durationStr}`;
        
        document.getElementById('pipeline-done-actions').classList.remove('hidden');
        
        fetchData();
    }

    init();
});
