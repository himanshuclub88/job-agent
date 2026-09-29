document.addEventListener('DOMContentLoaded', () => {
    /* --- State & Config --- */
    const API_URL = "http://localhost:8000/api/summary";
    const API_RUN_PIPELINE = "http://localhost:8000/api/run-pipeline";
    const API_PIPELINE_STATUS = "http://localhost:8000/api/pipeline-status";
    
    // Pipeline state
    let isPipelineRunning = false;
    let pipelineStartTime = 0;
    let localProgressTimer = null;
    let serverPollTimer = null;
    let devForceComplete = false;

    // Fallback Data
    const fallbackData = {
        "responsibilities": [
            { "company": "Indian MNC", "job_title": "AI Engineer", "text": "Share updated resume to hr@careersieve.com", "recruiter": "Rahul Kumar", "thread_id": "1a0d3060629a923e" },
            { "company": "I Novate", "job_title": "Lead AI Engineers", "text": "Apply for urgent AI Engineer openings", "recruiter": "Pankaj Kumar Gupta", "thread_id": "1a0d95ef59891a69" }
        ],
        "opportunities": [
            { "company": "Innovya Tech", "job_title": "Data Engineer", "location": "Pune", "source": "LinkedIn", "thread_id": "1a0eb3062ea6fd10", "url":"#" }
        ],
        "updates": [
            { "text": "Applied for 2 jobs on 23 Sep, including Lead AI Engineer at Virtusa.", "thread_id": "1a0d078501b3a6ea" }
        ],
        "upcoming": [
            { "company": "Databricks", "job_title": "Certification", "text": "Assessment scheduled.", "date": "2026-11-10", "time": "14:00 IST", "link": "#" }
        ],
        "dont_miss": [
            "Complete the Adecco feedback survey by the deadline on 2026-10-04."
        ]
    };

    /* --- Initialization --- */
    function init() {
        // Date Setup
        const today = new Date();
        const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const formattedDate = today.toLocaleDateString('en-US', dateOptions);
        
        document.getElementById('current-date').textContent = formattedDate;
        document.getElementById('pipeline-date-display').textContent = formattedDate; 

        // Load Settings
        loadSettings();

        // Load Data
        fetchData();
        
        // Setup Event Listeners
        setupEvents();
    }

    function loadSettings() {
        const theme = localStorage.getItem('theme') || 'light';
        const textSize = localStorage.getItem('textSize') || 'text-md';
        
        document.documentElement.setAttribute('data-theme', theme);
        document.getElementById('theme-select').value = theme;
        
        document.body.className = textSize;
        document.getElementById('text-size-select').value = textSize;
    }

    /* --- DOM Events --- */
    function setupEvents() {
        // Notifications Toggle
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

        // Settings Modal
        document.getElementById('nav-settings').addEventListener('click', (e) => {
            e.preventDefault();
            openModal('settings-modal');
        });
        document.getElementById('close-settings-btn').addEventListener('click', () => closeModal('settings-modal'));
        
        document.getElementById('theme-select').addEventListener('change', (e) => {
            document.documentElement.setAttribute('data-theme', e.target.value);
            localStorage.setItem('theme', e.target.value);
        });
        document.getElementById('text-size-select').addEventListener('change', (e) => {
            document.body.className = e.target.value;
            localStorage.setItem('textSize', e.target.value);
        });

        // Pipeline Modal Logic
        document.getElementById('nav-run-pipeline').addEventListener('click', (e) => {
            e.preventDefault();
            openModal('pipeline-modal');
            if (isPipelineRunning) {
                document.getElementById('pipeline-config-view').classList.add('hidden');
                document.getElementById('pipeline-progress-view').classList.remove('hidden');
            } else {
                document.getElementById('pipeline-config-view').classList.remove('hidden');
                document.getElementById('pipeline-progress-view').classList.add('hidden');
                // Reset UI in case it was previously finished
                document.getElementById('progress-spinner').classList.remove('hidden');
                document.getElementById('progress-success').classList.add('hidden');
                document.getElementById('completion-stats').classList.add('hidden');
                document.getElementById('pipeline-done-actions').classList.add('hidden');
                document.getElementById('progress-status-text').textContent = "Extracting emails & analyzing data...";
                document.getElementById('progress-subtext').classList.remove('hidden');
                document.getElementById('progress-fill').style.width = '0%';
                document.getElementById('progress-percentage').textContent = '0%';
                document.getElementById('progress-time').textContent = '0:00';
            }
        });
        
        document.getElementById('close-pipeline-btn').addEventListener('click', () => closeModal('pipeline-modal'));
        document.getElementById('done-pipeline-btn').addEventListener('click', () => closeModal('pipeline-modal'));
        
        // No more cancel button on config view. Modals can be closed by clicking the X or overlay.
        document.getElementById('modal-overlay').addEventListener('click', () => {
            closeModal('pipeline-modal');
            closeModal('settings-modal');
        });

        // Run Pipeline Logic
        document.getElementById('start-pipeline-btn').addEventListener('click', startPipeline);
        
        // Dev Fast Forward
        document.getElementById('dev-fast-forward').addEventListener('click', () => {
            devForceComplete = true;
        });
    }

    /* --- Data Fetching & Rendering --- */
    async function fetchData() {
        try {
            const res = await fetch(API_URL);
            if (!res.ok) throw new Error("API not accessible");
            const data = await res.json();
            renderUI(data);
        } catch (err) {
            console.log("Using fallback mock data.");
            renderUI(fallbackData);
        }
    }

    function renderUI(data) {
        if (data.dont_miss && data.dont_miss.length > 0) {
            document.getElementById('notif-badge').textContent = data.dont_miss.length;
            document.getElementById('notif-list').innerHTML = data.dont_miss.map(alert => `
                <div class="notif-item">
                    <i class="fa-solid fa-circle-exclamation"></i>
                    <div>${alert}</div>
                </div>
            `).join('');
        } else {
            document.getElementById('notif-list').innerHTML = '<div style="padding:15px;text-align:center;color:gray;">All caught up!</div>';
        }

        renderRows('responsibilities-list', 'resp-count', data.responsibilities, item => {
            const emailUrl = `https://mail.google.com/mail/u/1/#all/${item.thread_id}`;
            return `
            <div class="list-item">
                <div class="item-content">
                    <div class="item-title">${item.job_title ? item.job_title : item.company || 'Unknown'}</div>
                    <div class="item-desc">${item.text}</div>
                    <div class="item-badges">
                        ${item.company && item.job_title ? `<span class="pill">${item.company}</span>` : ''}
                        ${item.recruiter ? `<span class="pill"><i class="fa-regular fa-user"></i> ${item.recruiter}</span>` : ''}
                    </div>
                </div>
                <div class="item-actions">
                    <a href="${emailUrl}" target="_blank" class="btn btn-outline btn-sm"><i class="fa-regular fa-envelope"></i> Email</a>
                </div>
            </div>`;
        });

        renderRows('opportunities-list', 'opp-count', data.opportunities, item => {
            const emailUrl = `https://mail.google.com/mail/u/1/#all/${item.thread_id}`;
            return `
            <div class="list-item">
                <div class="item-content">
                    <div class="item-title">${item.job_title || 'Role Unspecified'}</div>
                    <div class="item-desc">${item.company || 'Unknown Company'}</div>
                    <div class="item-badges">
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

        renderRows('updates-list', 'update-count', data.updates, item => `
            <div class="feed-item">
                <div class="feed-meta">Update</div>
                <div class="feed-title">${item.text}</div>
                <a href="https://mail.google.com/mail/u/1/#all/${item.thread_id}" target="_blank" class="text-muted" style="font-size:0.8em;"><i class="fa-solid fa-arrow-right"></i> View Source</a>
            </div>
        `);

        renderRows('upcoming-list', 'upc-count', data.upcoming, item => `
            <div class="feed-item">
                <div class="feed-meta"><i class="fa-regular fa-clock"></i> ${item.date || ''} ${item.time ? 'at ' + item.time : ''}</div>
                <div class="feed-title">${item.text}</div>
                ${item.link ? `<a href="${item.link}" target="_blank" class="text-muted" style="font-size:0.8em;"><i class="fa-solid fa-link"></i> Link</a>` : ''}
            </div>
        `);
    }

    function renderRows(containerId, countId, items, templateFn) {
        const container = document.getElementById(containerId);
        const count = document.getElementById(countId);
        
        if (!items || items.length === 0) {
            container.innerHTML = '<div style="padding:30px;text-align:center;color:var(--text-muted);">No data available.</div>';
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

    async function startPipeline() {
        const startBtn = document.getElementById('start-pipeline-btn');
        startBtn.disabled = true; // Disable to prevent double click
        
        try {
            // Trigger backend (ignore failure for UI simulation if backend is off)
            fetch(API_RUN_PIPELINE, { method: 'POST' }).catch(e => console.log('Backend not available. Simulating.'));
        } catch(e) {}

        document.getElementById('pipeline-config-view').classList.add('hidden');
        document.getElementById('pipeline-progress-view').classList.remove('hidden');
        
        isPipelineRunning = true;
        pipelineStartTime = Date.now();
        devForceComplete = false;
        
        // Local interval for smooth visual progress bar update
        localProgressTimer = setInterval(updateVisualProgress, 1000);
        
        // Polling interval to check backend status
        serverPollTimer = setInterval(pollServerStatus, 3000);
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

        if (devForceComplete) {
            finishPipeline("Simulated fast forward.");
            return;
        }

        if (elapsedSec < 600) {
            p = (elapsedSec / 600) * 90;
        } else {
            let extraMin = (elapsedSec - 600) / 60;
            p = 90 + extraMin;
            if (p > 99) p = 99; // Stuck at 99% until server says done
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
                
                // If backend says it is finished and provides a duration
                if (status.is_running === false && status.duration_str) {
                    finishPipeline(status.duration_str, status.message);
                }
            }
        } catch (e) {
            // Backend offline, just rely on devForceComplete for simulation
        }
    }

    function finishPipeline(durationStr, messageOverride = null) {
        clearInterval(localProgressTimer);
        clearInterval(serverPollTimer);
        
        isPipelineRunning = false;
        document.getElementById('start-pipeline-btn').disabled = false; // re-enable for next time
        
        // Jump to 100%
        document.getElementById('progress-fill').style.width = '100%';
        document.getElementById('progress-percentage').textContent = '100%';
        
        // Update UI to success state
        document.getElementById('progress-spinner').classList.add('hidden');
        document.getElementById('progress-success').classList.remove('hidden');
        document.getElementById('progress-status-text').textContent = messageOverride || "Pipeline completed successfully!";
        document.getElementById('progress-subtext').classList.add('hidden');
        
        // Show actual duration stats panel
        const statsPanel = document.getElementById('completion-stats');
        statsPanel.classList.remove('hidden');
        document.getElementById('final-duration-text').textContent = `Task took ${durationStr}`;
        
        // Show close button
        document.getElementById('pipeline-done-actions').classList.remove('hidden');
        
        // Reload dashboard data
        fetchData();
    }

    init();
});
