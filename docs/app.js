let globalConfig = { pages: [] };
let globalState = { pages: {} };
let activePageIndex = -1;

document.addEventListener('DOMContentLoaded', () => {
    loadData();
});

async function loadData() {
    const savedToken = localStorage.getItem('ghToken');
    const savedRepo = localStorage.getItem('ghRepo');
    if (savedToken) document.getElementById('ghToken').value = savedToken;
    if (savedRepo) document.getElementById('ghRepo').value = savedRepo;

    try {
        const configRes = await fetch(`config.json?t=${Date.now()}`);
        if (configRes.ok) {
            const fetchedConfig = await configRes.json();
            
            // Prevent GitHub Pages deployment delay from wiping out recent saves
            const cachedTime = localStorage.getItem('cachedConfigTime');
            if (cachedTime && (Date.now() - parseInt(cachedTime)) < 3 * 60 * 1000) {
                console.log("Using recent local cache to bypass GitHub Pages 2-minute delay.");
                globalConfig = JSON.parse(localStorage.getItem('cachedConfig'));
            } else {
                globalConfig = fetchedConfig;
            }
        }
        
        const stateRes = await fetch(`state.json?t=${Date.now()}`);
        if (stateRes.ok) {
            globalState = await stateRes.json();
        }
    } catch (e) {
        console.log("Could not load local data: ", e);
    }
    
    if (!globalConfig.pages) globalConfig.pages = [];
    if (!globalState.pages) globalState.pages = {};
    
    renderPageSelector();
    renderInventoryPanel();
    
    // Auto-refresh inventory every 3 hours (10800000 ms)
    setInterval(async () => {
        console.log("Auto-refreshing inventory...");
        try {
            const stateRes = await fetch(`state.json?t=${Date.now()}`);
            if (stateRes.ok) {
                globalState = await stateRes.json();
                renderInventoryPanel();
                renderStats(globalConfig.pages[activePageIndex].page_name);
            }
        } catch(e) { console.log("Auto-refresh error:", e); }
    }, 3 * 60 * 60 * 1000);
}

function renderPageSelector() {
    const selector = document.getElementById('pageSelector');
    selector.innerHTML = '';
    
    if (globalConfig.pages.length === 0) {
        const opt = document.createElement('option');
        opt.text = "-- No Pages Configured --";
        selector.add(opt);
        document.getElementById('mainGrid').style.display = 'none';
        return;
    }
    
    globalConfig.pages.forEach((page, index) => {
        const opt = document.createElement('option');
        opt.value = index;
        opt.text = page.page_name;
        selector.add(opt);
    });
    
    document.getElementById('mainGrid').style.display = 'grid';
    
    if (activePageIndex === -1) activePageIndex = 0;
    selector.value = activePageIndex;
    switchPage();
}

function renderInventoryPanel() {
    const panel = document.getElementById('inventoryPanel');
    const tbody = document.getElementById('inventoryBody');
    if (!panel || !tbody) return;
    
    if (globalConfig.pages.length === 0) {
        panel.style.display = 'none';
        return;
    }
    
    panel.style.display = 'block';
    tbody.innerHTML = '';
    
    globalConfig.pages.forEach(page => {
        const pState = globalState.pages[page.page_name] || {};
        const imgLeft = pState.images_left;
        const dailyCount = pState.daily_count || 0;
        const freq = page.frequency || 6;
        const folder = page.cloudinary_folder || 'Not Set';
        
        const tr = document.createElement('tr');
        
        // Determine image count color
        let imgStyle = '';
        let imgDisplay = 'Unknown';
        if (imgLeft !== undefined) {
            imgDisplay = imgLeft;
            if (imgLeft < 10) {
                imgStyle = 'background: #e74c3c; color: white; padding: 4px 10px; border-radius: 12px; font-weight: bold;';
            } else if (imgLeft < 20) {
                imgStyle = 'background: #f39c12; color: white; padding: 4px 10px; border-radius: 12px; font-weight: bold;';
            } else {
                imgStyle = 'background: #2ecc71; color: white; padding: 4px 10px; border-radius: 12px; font-weight: bold;';
            }
        }
        
        // Determine status
        let status = '';
        if (dailyCount >= freq) {
            status = '<span style="color: #2ecc71; font-weight: bold;">✅ Target Met</span>';
        } else if (dailyCount > 0) {
            status = `<span style="color: #e67e22; font-weight: bold;">⚠️ ${dailyCount}/${freq} In Progress</span>`;
        } else {
            status = '<span style="color: #95a5a6;">💤 Waiting</span>';
        }
        
        tr.innerHTML = `
            <td><strong>${page.page_name}</strong></td>
            <td>${folder}</td>
            <td><span style="${imgStyle}">${imgDisplay}</span></td>
            <td>${dailyCount}</td>
            <td>${freq}/day</td>
            <td>${status}</td>
        `;
        tbody.appendChild(tr);
    });
    
    // Update last checked time
    const checkedEl = document.getElementById('inventoryLastChecked');
    if (checkedEl) {
        checkedEl.innerText = `Last checked: ${new Date().toLocaleString()}`;
    }
}

function switchPage() {
    const selector = document.getElementById('pageSelector');
    if (!selector.value || globalConfig.pages.length === 0) return;
    
    // Save current form data back to globalConfig before switching (if applicable)
    saveFormToLocalState();
    
    activePageIndex = parseInt(selector.value, 10);
    const page = globalConfig.pages[activePageIndex];
    
    document.getElementById('activePageTitle').innerText = `Config: ${page.page_name}`;
    document.getElementById('statsPageTitle').innerText = page.page_name;
    
    document.getElementById('cloudinaryFolder').value = page.cloudinary_folder || '';
    document.getElementById('frequency').value = page.frequency || 6;
    document.getElementById('aiPrompt').value = page.ai_prompt || '';
    document.getElementById('captions').value = (page.captions || []).join(',\n');
    updateCaptionCount();
    
    renderStats(page.page_name);

    // Update the Active Config Alert
    const alert = document.getElementById('activeConfigAlert');
    alert.style.display = 'block';
    document.getElementById('activeFolder').innerText = page.cloudinary_folder || 'None';
    document.getElementById('activeCaptionsCount').innerText = (page.captions || []).length;
}

function renderStats(pageName) {
    const state = globalState.pages[pageName] || {};
    const pageConfig = globalConfig.pages[activePageIndex] || {};
    
    document.getElementById('dailyCount').innerText = state.daily_count || 0;
    
    if (pageConfig.last_updated) {
        const d = new Date(pageConfig.last_updated);
        document.getElementById('lastUpdated').innerText = d.toLocaleString();
    } else {
        document.getElementById('lastUpdated').innerText = "Never";
    }

    if (state.last_run) {
        const d = new Date(state.last_run);
        document.getElementById('lastRun').innerText = d.toLocaleString();
    } else {
        document.getElementById('lastRun').innerText = "Never";
    }
    
    // Calculate Next Run
    let nextRunText = "Unknown";
    if (!state.last_run) {
        nextRunText = "Ready for next hourly check";
    } else {
        const last = new Date(state.last_run);
        const freq = pageConfig.frequency || 6;
        if (state.daily_count >= freq) {
            nextRunText = "Daily limit reached. Paused until tomorrow.";
        } else {
            const nextTime = new Date(last.getTime() + 60 * 60 * 1000); // Must wait 1 hour
            if (new Date() > nextTime) {
                nextRunText = "Eligible Now (Waiting for hourly 60% chance)";
            } else {
                nextRunText = `After ${nextTime.toLocaleTimeString()} (60% chance)`;
            }
        }
    }
    document.getElementById('nextRun').innerText = nextRunText;
    
    if (state.images_left !== undefined) {
        const el = document.getElementById('imagesLeft');
        el.innerText = state.images_left;
        if (state.images_left < 7) {
            el.style.background = "#e74c3c"; // Red warning
        } else {
            el.style.background = "#2ecc71"; // Green good
        }
    }

    const totalCaptions = pageConfig.captions ? pageConfig.captions.length : 0;
    const totalPosted = state.posted ? state.posted.length : 0;
    const uniqueRemaining = Math.max(0, totalCaptions - totalPosted);
    document.getElementById('captionsLeft').innerText = uniqueRemaining;

    const tbody = document.querySelector('#historyTable tbody');
    tbody.innerHTML = '';
    
    (state.posted || []).forEach(post => {
        const tr = document.createElement('tr');
        const d = new Date(post.time);
        const captionSnippet = post.caption ? (post.caption.substring(0, 50) + (post.caption.length > 50 ? '...' : '')) : 'N/A';
        tr.innerHTML = `
            <td>${d.toLocaleString()}</td>
            <td><span class="badge">Success</span></td>
            <td><span title="${post.caption || ''}">${captionSnippet}</span></td>
            <td><a href="${post.url}" target="_blank">View Post</a></td>
        `;
        tbody.appendChild(tr);
    });
}

function saveFormToLocalState() {
    if (activePageIndex >= 0 && activePageIndex < globalConfig.pages.length) {
        const page = globalConfig.pages[activePageIndex];
        page.cloudinary_folder = document.getElementById('cloudinaryFolder').value;
        page.frequency = parseInt(document.getElementById('frequency').value, 10);
        page.ai_prompt = document.getElementById('aiPrompt').value.trim();
        
        const captionsRaw = document.getElementById('captions').value;
        page.captions = captionsRaw.split(',').map(c => c.trim()).filter(c => c.length > 0);
        
        page.last_updated = new Date().toISOString();
        
        // Instantly update the UI so the user sees their changes applied
        document.getElementById('activeFolder').innerText = page.cloudinary_folder || 'None';
        document.getElementById('activeCaptionsCount').innerText = page.captions.length;
    }
}

function addNewPage() {
    const name = prompt("Enter the name of the new Facebook Page:");
    if (name && name.trim().length > 0) {
        saveFormToLocalState();
        globalConfig.pages.push({
            page_name: name.trim(),
            cloudinary_folder: "",
            frequency: 6,
            ai_prompt: "",
            captions: []
        });
        activePageIndex = globalConfig.pages.length - 1;
        renderPageSelector();
    }
}

function deleteCurrentPage() {
    if (activePageIndex >= 0) {
        const confirmDelete = confirm("Are you sure you want to delete this page configuration?");
        if (confirmDelete) {
            globalConfig.pages.splice(activePageIndex, 1);
            activePageIndex = -1;
            renderPageSelector();
        }
    }
}

function updateCaptionCount() {
    const text = document.getElementById('captions').value;
    const count = text.split(',').map(c => c.trim()).filter(c => c.length > 0).length;
    document.getElementById('captionQueueCount').innerText = count;
}

async function saveSettings() {
    saveFormToLocalState(); // Make sure latest edits are caught
    
    const token = document.getElementById('ghToken').value;
    const repo = document.getElementById('ghRepo').value;
    const statusEl = document.getElementById('saveStatus');
    
    if (!token || !repo) {
        statusEl.innerText = "GitHub Token and Repo name are required to save.";
        statusEl.style.color = "red";
        return;
    }

    // Save tokens locally so the user doesn't have to type them again
    localStorage.setItem('ghToken', token);
    localStorage.setItem('ghRepo', repo);
    
    // Save to local cache to prevent refresh wipeouts while GitHub Pages deploys
    localStorage.setItem('cachedConfig', JSON.stringify(globalConfig));
    localStorage.setItem('cachedConfigTime', Date.now());

    statusEl.innerText = "Saving ALL configurations to GitHub (takes ~2 mins to go live)...";
    statusEl.style.color = "orange";

    try {
        const getUrl = `https://api.github.com/repos/${repo}/contents/docs/config.json`;
        const getHeaders = {
            'Authorization': `token ${token}`,
            'Accept': 'application/vnd.github.v3+json'
        };
        
        let sha = null;
        try {
            const getRes = await fetch(getUrl, { headers: getHeaders });
            if (getRes.ok) {
                const data = await getRes.json();
                sha = data.sha;
            }
        } catch (e) {}

        const contentBase64 = btoa(unescape(encodeURIComponent(JSON.stringify(globalConfig, null, 2))));
        const bodyData = {
            message: "Update multi-page config via Dashboard",
            content: contentBase64
        };
        if (sha) bodyData.sha = sha;

        const putRes = await fetch(getUrl, {
            method: 'PUT',
            headers: getHeaders,
            body: JSON.stringify(bodyData)
        });

        if (putRes.ok) {
            statusEl.innerText = "✅ Successfully saved all pages! Automation will use this on next run.";
            statusEl.style.color = "green";
        } else {
            const err = await putRes.json();
            throw new Error(err.message);
        }

    } catch (error) {
        console.error(error);
        statusEl.innerText = `❌ Error: ${error.message}`;
        statusEl.style.color = "red";
    }
}
async function forceTestPost() {
    const page = globalConfig.pages[activePageIndex];
    if (!confirm(`🚀 Force an immediate post for "${page.page_name}"?`)) return;
    
    await triggerRobotAction('test', page.page_name);
}

async function refreshStatsOnDemand() {
    if (!confirm(`🔄 Refresh inventory counts for all pages?`)) return;
    await triggerRobotAction('refresh');
}

async function triggerRobotAction(type, pageName = '') {
    const token = document.getElementById('ghToken').value;
    const repo = document.getElementById('ghRepo').value;
    const statusDiv = document.getElementById('robotStatus');
    const statusMsg = document.getElementById('statusMessage');

    if (!token || !repo) {
        alert("GitHub Token and Repo required. Please enter them and click 'Save ALL Configurations' first.");
        return;
    }

    statusDiv.style.display = 'block';
    statusMsg.innerText = type === 'test' ? `⏳ Waking up robot to post to ${pageName}...` : `⏳ Waking up robot to count images...`;

    try {
        // Record current state to detect changes
        const pageToWatch = pageName || (globalConfig.pages[activePageIndex] ? globalConfig.pages[activePageIndex].page_name : null);
        const originalLastRun = globalState.pages[pageToWatch]?.last_run;
        const originalImgCount = globalState.pages[pageToWatch]?.images_left;

        const url = `https://api.github.com/repos/${repo}/actions/workflows/auto_post.yml/dispatches`;
        const inputs = type === 'test' ? { test_page_name: pageName } : { refresh_only: 'true' };
        
        const res = await fetch(url, {
            method: 'POST',
            headers: { 
                'Authorization': `token ${token}`, 
                'Accept': 'application/vnd.github.v3+json' 
            },
            body: JSON.stringify({ ref: 'main', inputs })
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.message || "Failed to trigger GitHub Action.");
        }

        statusMsg.innerText = `🤖 Robot is working (this takes 1-2 minutes)...`;
        
        // Start polling for state.json changes
        await pollForStateUpdate(pageToWatch, originalLastRun, originalImgCount);
        
        statusMsg.innerText = `✅ Done! Dashboard Updated.`;
        setTimeout(() => { statusDiv.style.display = 'none'; }, 5000);

    } catch (e) {
        console.error(e);
        alert("Error: " + e.message);
        statusDiv.style.display = 'none';
    }
}

async function pollForStateUpdate(pageName, oldRun, oldCount) {
    const maxAttempts = 30; // 300 seconds total
    for (let i = 0; i < maxAttempts; i++) {
        await new Promise(r => setTimeout(r, 10000)); // Wait 10s
        
        try {
            // Force bypass cache by adding timestamp
            const res = await fetch(`state.json?t=${Date.now()}`);
            if (res.ok) {
                const newState = await res.json();
                const pageState = newState.pages[pageName];
                
                if (pageState && (pageState.last_run !== oldRun || pageState.images_left !== oldCount)) {
                    globalState = newState;
                    renderStats(globalConfig.pages[activePageIndex].page_name);
                    renderInventoryPanel();
                    return;
                }
            }
        } catch (e) { console.log("Polling error:", e); }
    }
    throw new Error("Robot took too long to respond. Please refresh the page manually in a minute.");
}
