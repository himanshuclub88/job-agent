document.addEventListener('DOMContentLoaded', () => {
    /* --- API --- */
    const API_URL = "http://127.0.0.1:8000/api/summary";
    const API_RUN_PIPELINE = "http://127.0.0.1:8000/api/run-pipeline";
    const API_PIPELINE_STATUS = "http://127.0.0.1:8000/api/pipeline-status";
    const API_REPLY_STATUS = "http://127.0.0.1:8000/api/reply-status";
    const API_GENERATE_REPLY = "http://127.0.0.1:8000/api/generate-reply";
    const API_CREATE_DRAFT = "http://127.0.0.1:8000/api/create-reply-draft";
    const API_SEND_REPLY = "http://127.0.0.1:8000/api/send-reply";

    /* --- UI / Pipeline State --- */
    const PIPELINE_STARTED_AT_KEY = 'ai-assistant-pipeline-started-at';
    const POLL_INTERVAL = 1500;

    let isPipelineRunning = false;
    let pipelineStartTime = 0;
    let progressTimer = null;
    let serverPollTimer = null;
    let pollInFlight = false;
    let lastRenderedLogCount = 0;
    let statusErrorCount = 0;
    let activeModalId = null;

    /* --- Reply Agent State --- */
    let activeReplyMessageId = null;
    let activeReplyThreadId = null;
    let replyGenerating = false;
    const replySentByMessageId = new Map();

    /* --- Dashboard State --- */
    let currentFilter = 'all';
    let currentSearch = '';
    let globalData = null;
    let searchDebounceTimer = null;

    const emptyData = {
        last_run: null,
        last_run_duration: null,
        responsibilities: [],
        opportunities: [],
        updates: [],
        upcoming: [],
        dont_miss: []
    };

    /* --- Initialization --- */
    async function init() {
        const today = new Date();
        const formattedDate = today.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });

        document.getElementById('current-date').textContent = formattedDate;
        document.getElementById('pipeline-date-display').textContent = formattedDate;

        loadSettings();
        setupEvents();

        await fetchData();
        await recoverPipelineState();
    }

    /* --- Settings --- */
    function applyTheme(theme) {
        const allowedThemes = ['light', 'dark', 'midnight', 'emerald', 'sunset'];
        if (!allowedThemes.includes(theme)) theme = 'light';

        document.documentElement.setAttribute('data-theme', theme);
        document.getElementById('theme-select').value = theme;
        localStorage.setItem('theme', theme);

        document.querySelectorAll('.theme-dot').forEach(dot => {
            dot.classList.toggle('active', dot.getAttribute('data-theme-val') === theme);
        });
    }

    function loadSettings() {
        const theme = localStorage.getItem('theme') || 'light';
        const allowedTextSizes = ['text-sm', 'text-md', 'text-lg'];
        const storedTextSize = localStorage.getItem('textSize') || 'text-md';
        const textSize = allowedTextSizes.includes(storedTextSize) ? storedTextSize : 'text-md';

        applyTheme(theme);
        document.body.className = textSize;
        document.getElementById('text-size-select').value = textSize;
    }

    /* --- Formatting --- */
    function formatReceivedDate(isoStr) {
        if (!isoStr) return '';

        try {
            const d = new Date(isoStr);
            if (Number.isNaN(d.getTime())) return isoStr;

            const now = new Date();
            const diffHours = Math.round((now - d) / (1000 * 60 * 60));

            if (diffHours >= 0 && diffHours < 24) {
                return diffHours === 0 ? 'Just now' : `${diffHours}h ago`;
            }

            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        } catch (e) {
            return isoStr;
        }
    }

    function formatTime(seconds) {
        seconds = Math.max(0, Number(seconds) || 0);
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}:${s < 10 ? '0' : ''}${s}`;
    }

    function getElapsedSeconds() {
        if (!pipelineStartTime) return 0;
        return Math.max(0, (Date.now() - pipelineStartTime) / 1000);
    }

    /* --- Dashboard Events --- */
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

            clearTimeout(searchDebounceTimer);
            searchDebounceTimer = setTimeout(filterAndRender, 120);
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

        document.getElementById('close-settings-btn').addEventListener('click', () => {
            closeModal('settings-modal');
        });

        document.getElementById('theme-select').addEventListener('change', (e) => {
            applyTheme(e.target.value);
        });

        document.querySelectorAll('.theme-dot').forEach(dot => {
            dot.addEventListener('click', () => {
                applyTheme(dot.getAttribute('data-theme-val'));
            });
        });

        document.getElementById('text-size-select').addEventListener('change', (e) => {
            document.body.className = e.target.value;
            localStorage.setItem('textSize', e.target.value);
        });

        document.getElementById('nav-run-pipeline').addEventListener('click', (e) => {
            e.preventDefault();
            openModal('pipeline-modal');
            renderPipelineView();
        });

        document.getElementById('close-pipeline-btn').addEventListener('click', () => {
            closeModal('pipeline-modal');
        });

        document.getElementById('done-pipeline-btn').addEventListener('click', () => {
            closeModal('pipeline-modal');
            fetchData();
        });

        document.getElementById('modal-overlay').addEventListener('click', () => {
            if (activeModalId) closeModal(activeModalId);
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && activeModalId) {
                closeModal(activeModalId);
            }
        });

        document.getElementById('start-pipeline-btn').addEventListener('click', startPipeline);

        document.getElementById('close-reply-btn').addEventListener('click', () => {
            closeModal('reply-modal');
        });

        document.getElementById('generate-again-btn').addEventListener('click', () => {
            if (activeReplyMessageId && activeReplyThreadId) {
                generateReply(activeReplyMessageId, activeReplyThreadId, true);
            }
        });

        document.getElementById('open-gmail-reply-btn').addEventListener('click', openGmailReply);

        document.getElementById('send-reply-btn').addEventListener('click', sendReply);
    }

    /* --- Dashboard Data --- */
    async function fetchData() {
        try {
            const res = await fetch(API_URL);
            if (!res.ok) throw new Error(`Summary API returned HTTP ${res.status}`);

            globalData = await res.json();

            // Load persisted reply state so sent replies are shown as completed.
            replySentByMessageId.clear();
            const responsibilityItems = Array.isArray(globalData.responsibilities) ? globalData.responsibilities : [];
            await Promise.all(responsibilityItems.map(async (item) => {
                if (!item.message_id) return;
                try {
                    const statusRes = await fetch(`${API_REPLY_STATUS}/${encodeURIComponent(item.message_id)}`);
                    if (!statusRes.ok) return;
                    const status = await statusRes.json();
                    replySentByMessageId.set(item.message_id, status.reply_sent === true);
                } catch (_) {
                    // Keep the existing dashboard usable if a reply-status check fails.
                }
            }));

            filterAndRender();
            return true;
        } catch (err) {
            console.warn('Unable to load dashboard data:', err);
            globalData = emptyData;
            filterAndRender();
            return false;
        }
    }

    function itemMatches(item = {}) {
        const combinedText = [
            item.company,
            item.job_title,
            item.text,
            item.recruiter,
            item.location,
            item.source
        ].filter(Boolean).join(' ').toLowerCase();

        if (currentSearch && !combinedText.includes(currentSearch)) {
            return false;
        }

        if (currentFilter === 'all') return true;
        if (currentFilter === 'ai') {
            return combinedText.includes('ai') || combinedText.includes('genai') || combinedText.includes('gpt');
        }
        if (currentFilter === 'data') {
            return combinedText.includes('data') || combinedText.includes('pyspark') || combinedText.includes('spark') || combinedText.includes('sql');
        }
        if (currentFilter === 'remote') return combinedText.includes('remote');
        if (currentFilter === 'action') {
            return combinedText.includes('dm') || combinedText.includes('contact') || combinedText.includes('resume') || combinedText.includes('apply');
        }

        return true;
    }

    function filterAndRender() {
        if (!globalData) return;

        const alerts = Array.isArray(globalData.dont_miss) ? globalData.dont_miss : [];
        const notifBadge = document.getElementById('notif-badge');
        const notifList = document.getElementById('notif-list');

        notifBadge.textContent = alerts.length;
        notifList.innerHTML = alerts.length
            ? alerts.map(alert => `
                <div class="notif-item">
                    <i class="fa-solid fa-circle-exclamation"></i>
                    <div>${alert}</div>
                </div>
            `).join('')
            : '<div style="padding:15px;text-align:center;color:var(--text-muted);">All caught up!</div>';

        const responsibilities = (globalData.responsibilities || []).filter(itemMatches);
        const opportunities = (globalData.opportunities || []).filter(itemMatches);
        const updates = (globalData.updates || []).filter(itemMatches);
        const upcoming = (globalData.upcoming || []).filter(itemMatches);

        renderRows('responsibilities-list', 'resp-count', responsibilities, item => {
            const emailUrl = `https://mail.google.com/mail/u/1/#all/${item.thread_id}`;
            const receivedText = formatReceivedDate(item.received_at);

            return `
            <div class="list-item">
                <div class="item-content">
                    <div class="item-title">${item.job_title ? item.job_title : item.company || 'Unknown'}</div>
                    <div class="item-desc">${item.text || ''}</div>
                    <div class="item-badges">
                        ${receivedText ? `<span class="pill received-pill"><i class="fa-regular fa-clock"></i> Recv ${receivedText}</span>` : ''}
                        ${item.company && item.job_title ? `<span class="pill">${item.company}</span>` : ''}
                        ${item.recruiter ? `<span class="pill"><i class="fa-regular fa-user"></i> ${item.recruiter}</span>` : ''}
                    </div>
                </div>
                <div class="item-actions">
                    ${replySentByMessageId.get(item.message_id) === true
                        ? `<span class="btn btn-outline btn-sm reply-completed"><i class="fa-solid fa-circle-check"></i> Replied</span>`
                        : `<button class="btn btn-primary btn-sm reply-btn" data-message-id="${item.message_id}" data-thread-id="${item.thread_id}">
                            <i class="fa-solid fa-reply"></i> Reply
                        </button>`}
                    <a href="${emailUrl}" target="_blank" class="btn btn-outline btn-sm"><i class="fa-regular fa-envelope"></i> Email</a>
                </div>
            </div>`;
        });

        renderRows('opportunities-list', 'opp-count', opportunities, item => {
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

        renderRows('updates-list', 'update-count', updates, item => {
            const receivedText = formatReceivedDate(item.received_at);

            return `
            <div class="feed-item">
                <div class="feed-meta">
                    <span><i class="fa-solid fa-circle-check" style="margin-right: 4px;"></i> Update</span>
                    ${receivedText ? `<span style="margin-left:auto; font-weight:normal; font-size:0.9em; color:var(--text-muted);">${receivedText}</span>` : ''}
                </div>
                <div class="feed-title">${item.text || ''}</div>
                <a href="https://mail.google.com/mail/u/1/#all/${item.thread_id}" target="_blank" class="text-muted" style="font-size:0.85em;"><i class="fa-solid fa-arrow-right"></i> View Source</a>
            </div>`;
        });

        renderRows('upcoming-list', 'upc-count', upcoming, item => {
            const receivedText = formatReceivedDate(item.received_at);

            return `
            <div class="feed-item">
                <div class="feed-meta" style="color: var(--warning);">
                    <span><i class="fa-regular fa-clock" style="margin-right: 4px;"></i> ${item.date || ''} ${item.time ? 'at ' + item.time : ''}</span>
                    ${receivedText ? `<span style="margin-left:auto; font-weight:normal; font-size:0.9em; color:var(--text-muted);">${receivedText}</span>` : ''}
                </div>
                <div class="feed-title">${item.text || ''}</div>
                ${item.link ? `<a href="${item.link}" target="_blank" class="text-muted" style="font-size:0.85em;"><i class="fa-solid fa-link"></i> External Link</a>` : ''}
            </div>`;
        });
    }

    /* --- Reply Agent --- */
    async function openReplyForItem(messageId, threadId) {
        if (!messageId || !threadId) return;
        activeReplyMessageId = messageId;
        activeReplyThreadId = threadId;
        const replyText = document.getElementById('reply-text');
        const statusText = document.getElementById('reply-status-text');
        const generateBtn = document.getElementById('generate-again-btn');
        const openGmailBtn = document.getElementById('open-gmail-reply-btn');
        const sendBtn = document.getElementById('send-reply-btn');
        replyText.value = '';
        statusText.textContent = 'Checking whether a reply is needed...';
        statusText.className = 'reply-status-text';
        generateBtn.disabled = true;
        openGmailBtn.disabled = true;
        sendBtn.disabled = true;
        openModal('reply-modal');
        try {
            const statusRes = await fetch(`${API_REPLY_STATUS}/${encodeURIComponent(messageId)}`);
            if (!statusRes.ok) throw new Error(`Reply status API returned HTTP ${statusRes.status}`);
            const status = await statusRes.json();
            if (status.status !== 'reply_needed' || status.need_to_reply !== true) {
                statusText.textContent = 'No reply is required for this email.';
                statusText.classList.add('reply-status-muted');
                return;
            }
            statusText.textContent = 'Reply needed. Generating reply...';
            await generateReply(messageId, status.thread_id || threadId, false);
        } catch (error) {
            statusText.textContent = `Unable to check reply status: ${error.message}`;
            statusText.className = 'reply-status-text reply-status-error';
        }
    }

    async function generateReply(messageId, threadId, force = false) {
        if (replyGenerating) return;
        const replyText = document.getElementById('reply-text');
        const statusText = document.getElementById('reply-status-text');
        const generateBtn = document.getElementById('generate-again-btn');
        const openGmailBtn = document.getElementById('open-gmail-reply-btn');
        const sendBtn = document.getElementById('send-reply-btn');
        replyGenerating = true;
        generateBtn.disabled = true;
        openGmailBtn.disabled = true;
        sendBtn.disabled = true;
        statusText.textContent = force ? 'Generating a new reply...' : 'Generating reply...';
        statusText.className = 'reply-status-text';
        replyText.value = '';
        try {
            const payload = { message_id: messageId, thread_id: threadId, generate_again: force, force: force };
            const res = await fetch(API_GENERATE_REPLY, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            });
            if (!res.ok) {
                let detail = `HTTP ${res.status}`;
                try { const errorData = await res.json(); detail = errorData.detail || detail; } catch (_) {}
                throw new Error(detail);
            }
            const data = await res.json();
            const reply = data.reply || data.generated_reply || '';
            if (!reply) throw new Error('Backend returned an empty reply.');
            replyText.value = reply;
            statusText.textContent = force ? 'New reply generated.' : 'Reply generated.';
            generateBtn.disabled = false;
            openGmailBtn.disabled = false;
            sendBtn.disabled = false;
        } catch (error) {
            statusText.textContent = `Unable to generate reply: ${error.message}`;
            statusText.className = 'reply-status-text reply-status-error';
        } finally {
            replyGenerating = false;
            if (!replyText.value) generateBtn.disabled = true;
        }
    }

    async function openGmailReply() {
        if (!activeReplyMessageId || !activeReplyThreadId) return;
        const replyText = document.getElementById('reply-text');
        const statusText = document.getElementById('reply-status-text');
        const openGmailBtn = document.getElementById('open-gmail-reply-btn');
        const sendBtn = document.getElementById('send-reply-btn');
        const reply = replyText.value.trim();

        if (!reply) {
            statusText.textContent = 'Reply is empty.';
            statusText.className = 'reply-status-text reply-status-error';
            return;
        }

        openGmailBtn.disabled = true;
        sendBtn.disabled = true;
        statusText.textContent = 'Preparing Gmail reply draft...';
        statusText.className = 'reply-status-text';

        try {
            const res = await fetch(API_CREATE_DRAFT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message_id: activeReplyMessageId,
                    thread_id: activeReplyThreadId,
                    reply,
                }),
            });
            if (!res.ok) {
                let detail = `HTTP ${res.status}`;
                try { const errorData = await res.json(); detail = errorData.detail || detail; } catch (_) {}
                throw new Error(detail);
            }

            window.open(`https://mail.google.com/mail/u/1/#all/${activeReplyThreadId}`, '_blank');
            statusText.textContent = 'Draft opened in the same Gmail thread.';
            openGmailBtn.disabled = false;
            sendBtn.disabled = false;
        } catch (error) {
            statusText.textContent = `Unable to open Gmail draft: ${error.message}`;
            statusText.className = 'reply-status-text reply-status-error';
            openGmailBtn.disabled = false;
            sendBtn.disabled = false;
        }
    }

    async function sendReply() {
        if (!activeReplyMessageId || !activeReplyThreadId) return;
        const replyText = document.getElementById('reply-text');
        const statusText = document.getElementById('reply-status-text');
        const sendBtn = document.getElementById('send-reply-btn');
        const generateBtn = document.getElementById('generate-again-btn');
        const openGmailBtn = document.getElementById('open-gmail-reply-btn');
        const reply = replyText.value.trim();

        if (!reply) {
            statusText.textContent = 'Reply is empty.';
            statusText.className = 'reply-status-text reply-status-error';
            return;
        }

        sendBtn.disabled = true;
        generateBtn.disabled = true;
        openGmailBtn.disabled = true;
        statusText.textContent = 'Sending reply...';
        statusText.className = 'reply-status-text';

        try {
            const res = await fetch(API_SEND_REPLY, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message_id: activeReplyMessageId,
                    thread_id: activeReplyThreadId,
                    reply,
                }),
            });
            if (!res.ok) {
                let detail = `HTTP ${res.status}`;
                try { const errorData = await res.json(); detail = errorData.detail || detail; } catch (_) {}
                throw new Error(detail);
            }

            statusText.textContent = 'Reply sent successfully.';
            statusText.className = 'reply-status-text';
            replyText.disabled = true;
            replySentByMessageId.set(activeReplyMessageId, true);
            await fetchData();
        } catch (error) {
            statusText.textContent = `Unable to send reply: ${error.message}`;
            statusText.className = 'reply-status-text reply-status-error';
            sendBtn.disabled = false;
            generateBtn.disabled = false;
            openGmailBtn.disabled = false;
        }
    }

    document.addEventListener('click', (event) => {
        const button = event.target.closest('.reply-btn');
        if (!button) return;
        event.preventDefault();
        openReplyForItem(button.dataset.messageId, button.dataset.threadId);
    });

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

    /* --- Modal Logic --- */
    function openModal(id) {
        document.querySelectorAll('.modal').forEach(modal => modal.classList.add('hidden'));
        document.getElementById('modal-overlay').classList.remove('hidden');
        document.getElementById(id).classList.remove('hidden');
        activeModalId = id;
    }

    function closeModal(id) {
        document.getElementById(id)?.classList.add('hidden');

        if (activeModalId === id) {
            activeModalId = null;
            document.getElementById('modal-overlay').classList.add('hidden');
        }
    }

    /* --- Pipeline UI --- */
    function resetPipelineProgressUI() {
        document.getElementById('progress-spinner').classList.remove('hidden');
        document.getElementById('progress-success').classList.add('hidden');
        document.getElementById('progress-failure').classList.add('hidden');
        document.getElementById('completion-stats').classList.add('hidden');
        document.getElementById('pipeline-done-actions').classList.add('hidden');

        const fill = document.getElementById('progress-fill');
        fill.style.width = '0%';
        fill.style.background = '';
        fill.classList.add('gradient-bar');

        const percentage = document.getElementById('progress-percentage');
        percentage.textContent = '0%';
        percentage.style.color = 'var(--primary)';

        document.getElementById('progress-time').textContent = '0:00';
        document.getElementById('progress-status-text').textContent = 'Extracting emails & analyzing data...';
        document.getElementById('progress-subtext').classList.remove('hidden');
        document.getElementById('terminal-step-badge').textContent = 'Starting';
    }

    function showPipelineConfig() {
        document.getElementById('pipeline-config-view').classList.remove('hidden');
        document.getElementById('pipeline-progress-view').classList.add('hidden');
        document.getElementById('start-pipeline-btn').disabled = false;

        document.getElementById('last-run-time-val').textContent = globalData?.last_run || 'Not recorded yet';
        document.getElementById('last-run-duration-val').textContent = globalData?.last_run_duration || '--';
    }

    function showPipelineProgress() {
        document.getElementById('pipeline-config-view').classList.add('hidden');
        document.getElementById('pipeline-progress-view').classList.remove('hidden');
        document.getElementById('start-pipeline-btn').disabled = true;
    }

    function renderPipelineView() {
        if (isPipelineRunning) {
            showPipelineProgress();
            updateVisualProgress();
            return;
        }

        showPipelineConfig();
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

    function clearPipelineTimers() {
        if (progressTimer) {
            clearInterval(progressTimer);
            progressTimer = null;
        }

        if (serverPollTimer) {
            clearTimeout(serverPollTimer);
            serverPollTimer = null;
        }

        pollInFlight = false;
    }

    function startProgressTimer() {
        if (progressTimer) return;
        updateVisualProgress();
        progressTimer = setInterval(updateVisualProgress, 1000);
    }

    function scheduleNextPoll(delay = POLL_INTERVAL) {
        if (!isPipelineRunning) return;
        clearTimeout(serverPollTimer);
        serverPollTimer = setTimeout(pollServerStatus, delay);
    }

    async function startPipeline() {
        if (isPipelineRunning) {
            renderPipelineView();
            return;
        }

        const startBtn = document.getElementById('start-pipeline-btn');
        startBtn.disabled = true;

        showPipelineProgress();
        resetPipelineProgressUI();
        document.getElementById('terminal-body').innerHTML = '';
        appendTerminalLog('Initializing connection to backend API...', 'Init');

        try {
            const res = await fetch(API_RUN_PIPELINE, { method: 'POST' });

            if (!res.ok) {
                throw new Error(`Backend returned HTTP ${res.status}`);
            }

            // The existing API does not need to return a run ID. We keep the
            // start timestamp locally so the UI can recover after a refresh.
            pipelineStartTime = Date.now();
            localStorage.setItem(PIPELINE_STARTED_AT_KEY, String(pipelineStartTime));
            isPipelineRunning = true;
            lastRenderedLogCount = 0;
            statusErrorCount = 0;

            appendTerminalLog('Backend acknowledged. Background task started.', 'Running');
            startProgressTimer();

            // Poll immediately instead of waiting for the first interval.
            await pollServerStatus();
        } catch (e) {
            isPipelineRunning = false;
            pipelineStartTime = 0;
            localStorage.removeItem(PIPELINE_STARTED_AT_KEY);
            clearPipelineTimers();

            appendTerminalLog(`Unable to start pipeline: ${e.message}`, 'Failed');
            appendTerminalLog('Make sure the local backend server is running.', 'Info');
            document.getElementById('progress-status-text').textContent = 'Pipeline could not be started.';
            document.getElementById('progress-subtext').textContent = 'Check the local backend and try again.';
            document.getElementById('progress-spinner').classList.add('hidden');
            document.getElementById('progress-failure').classList.remove('hidden');
            document.getElementById('pipeline-done-actions').classList.remove('hidden');
            startBtn.disabled = false;
        }
    }

    /* --- Pipeline Progress --- */
    function updateVisualProgress(serverStatus = null) {
        if (!isPipelineRunning) return;

        const elapsedSec = getElapsedSeconds();
        let progress = null;

        // Use backend progress when available. Otherwise retain the old
        // time-based estimate as a visual fallback.
        if (serverStatus && Number.isFinite(Number(serverStatus.progress))) {
            progress = Math.max(0, Math.min(99, Number(serverStatus.progress)));
        }

        if (progress === null) {
            if (elapsedSec < 600) {
                progress = (elapsedSec / 600) * 90;
            } else {
                progress = Math.min(99, 90 + ((elapsedSec - 600) / 60));
            }
        }

        document.getElementById('progress-fill').style.width = `${progress}%`;
        document.getElementById('progress-percentage').textContent = `${Math.floor(progress)}%`;
        document.getElementById('progress-time').textContent = formatTime(elapsedSec);
    }

    function updatePipelineFromStatus(status) {
        if (!status) return;

        if (status.started_at && !localStorage.getItem(PIPELINE_STARTED_AT_KEY)) {
            const parsed = new Date(status.started_at).getTime();
            if (!Number.isNaN(parsed)) {
                pipelineStartTime = parsed;
                localStorage.setItem(PIPELINE_STARTED_AT_KEY, String(parsed));
            }
        }

        if (status.current_step) {
            document.getElementById('terminal-step-badge').textContent = status.current_step;
        }

        if (status.current_step) {
            document.getElementById('progress-status-text').textContent = status.current_step;
        }

        updateVisualProgress(status);

        if (Array.isArray(status.logs)) {
            if (status.logs.length < lastRenderedLogCount) {
                // Backend restarted/reset its log buffer.
                lastRenderedLogCount = 0;
                document.getElementById('terminal-body').innerHTML = '';
            }

            if (status.logs.length > lastRenderedLogCount) {
                const newLogs = status.logs.slice(lastRenderedLogCount);
                newLogs.forEach(logLine => appendTerminalLog(logLine, status.current_step));
                lastRenderedLogCount = status.logs.length;
            }
        }
    }

    async function recoverPipelineState() {
        try {
            const res = await fetch(API_PIPELINE_STATUS);
            if (!res.ok) return;

            const status = await res.json();

            if (status.is_running === true) {
                const savedStart = Number(localStorage.getItem(PIPELINE_STARTED_AT_KEY));
                const serverStart = status.started_at ? new Date(status.started_at).getTime() : 0;

                pipelineStartTime = Number.isFinite(savedStart) && savedStart > 0
                    ? savedStart
                    : (Number.isFinite(serverStart) && serverStart > 0 ? serverStart : Date.now());

                localStorage.setItem(PIPELINE_STARTED_AT_KEY, String(pipelineStartTime));
                isPipelineRunning = true;
                lastRenderedLogCount = 0;
                statusErrorCount = 0;

                resetPipelineProgressUI();
                document.getElementById('terminal-body').innerHTML = '';
                showPipelineProgress();
                updatePipelineFromStatus(status);
                startProgressTimer();
                scheduleNextPoll(0);
            } else {
                localStorage.removeItem(PIPELINE_STARTED_AT_KEY);
            }
        } catch (e) {
            // If the backend is unavailable at page load, do not invent a running state.
            // The next manual pipeline open/start will try again.
            console.warn('Could not recover pipeline state:', e);
        }
    }

    async function pollServerStatus() {
        if (!isPipelineRunning || pollInFlight) return;

        pollInFlight = true;
        let shouldSchedule = true;

        try {
            const res = await fetch(API_PIPELINE_STATUS);

            if (!res.ok) {
                throw new Error(`Status API returned HTTP ${res.status}`);
            }

            const status = await res.json();
            statusErrorCount = 0;
            updatePipelineFromStatus(status);

            if (status.is_running === false) {
                shouldSchedule = false;
                finishPipeline(status);
            }
        } catch (e) {
            statusErrorCount += 1;

            // Do not stop the pipeline because of a temporary local network hiccup.
            // Give the user a small visual indication after repeated failures.
            if (statusErrorCount === 3) {
                document.getElementById('progress-subtext').textContent = 'Waiting for the local backend... execution may still be running.';
                appendTerminalLog('Status check temporarily unavailable; will keep trying.', 'Waiting');
            }
        } finally {
            pollInFlight = false;

            if (shouldSchedule && isPipelineRunning) {
                scheduleNextPoll(POLL_INTERVAL);
            }
        }
    }

    function finishPipeline(status = {}) {
        clearPipelineTimers();
        isPipelineRunning = false;
        localStorage.removeItem(PIPELINE_STARTED_AT_KEY);

        const failed = status.success === false ||
            status.status === 'failed' ||
            status.status === 'error' ||
            status.status === 'stopped' ||
            status.duration_str === 'Failed';

        const fillBar = document.getElementById('progress-fill');
        const percentageTxt = document.getElementById('progress-percentage');
        const spinner = document.getElementById('progress-spinner');
        const successIcon = document.getElementById('progress-success');
        const failureIcon = document.getElementById('progress-failure');
        const subtext = document.getElementById('progress-subtext');
        const doneActions = document.getElementById('pipeline-done-actions');

        spinner.classList.add('hidden');
        successIcon.classList.toggle('hidden', failed);
        failureIcon.classList.toggle('hidden', !failed);

        fillBar.style.width = '100%';
        fillBar.classList.remove('gradient-bar');
        fillBar.style.background = failed ? 'var(--danger)' : 'var(--success)';

        percentageTxt.textContent = '100%';
        percentageTxt.style.color = failed ? 'var(--danger)' : 'var(--success)';

        document.getElementById('progress-status-text').textContent = failed
            ? (status.message || 'Pipeline failed or stopped.')
            : (status.message || 'Pipeline processing complete!');

        subtext.classList.add('hidden');

        const statsPanel = document.getElementById('completion-stats');
        statsPanel.classList.remove('hidden');
        statsPanel.classList.toggle('pipeline-failed', failed);
        document.getElementById('final-duration-text').textContent = status.duration_str && status.duration_str !== 'Failed'
            ? `Task completed in ${status.duration_str}`
            : `Task ran for ${formatTime(getElapsedSeconds())}`;

        doneActions.classList.remove('hidden');
        document.getElementById('start-pipeline-btn').disabled = false;

        if (!failed) {
            // Refresh the dashboard once the backend has finished writing its results.
            fetchData();
        }
    }

    init();
});
