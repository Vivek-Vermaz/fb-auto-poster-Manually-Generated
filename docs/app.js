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
        const configRes = await fetch('config.json');
        if (configRes.ok) {
            globalConfig = await configRes.json();
        }
        
        const stateRes = await fetch('state.json');
        if (stateRes.ok) {
            globalState = await stateRes.json();
        }
    } catch (e) {
        console.log("Could not load local data: ", e);
    }
    
    if (!globalConfig.pages) globalConfig.pages = [];
    if (!globalState.pages) globalState.pages = {};
    
    renderPageSelector();
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
    document.getElementById('captions').value = (page.captions || []).join(',\n');
    
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
        
        const captionsRaw = document.getElementById('captions').value;
        page.captions = captionsRaw.split(',').map(c => c.trim()).filter(c => c.length > 0);
        
        page.last_updated = new Date().toISOString();
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

    statusEl.innerText = "Saving ALL configurations to GitHub...";
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
    const selector = document.getElementById('pageSelector');
    const pageIndex = parseInt(selector.value, 10);
    if (isNaN(pageIndex)) return;

    const page = globalConfig.pages[pageIndex];
    const token = document.getElementById('ghToken').value;
    const repo = document.getElementById('ghRepo').value;

    if (!token || !repo) {
        alert("GitHub Token and Repo name are required to trigger a test post.");
        return;
    }

    if (!confirm(`🚀 This will force an immediate post to Facebook for "${page.page_name}", bypassing all schedules and probabilities. Continue?`)) {
        return;
    }

    const btn = event.target;
    const originalText = btn.innerText;
    btn.innerText = "⏳ Triggering...";
    btn.disabled = true;

    try {
        const url = `https://api.github.com/repos/${repo}/actions/workflows/auto_post.yml/dispatches`;
        const res = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `token ${token}`,
                'Accept': 'application/vnd.github.v3+json'
            },
            body: JSON.stringify({
                ref: 'main',
                inputs: {
                    test_page_name: page.page_name
                }
            })
        });

        if (res.ok) {
            alert("✅ Test post triggered! It will appear on Facebook in about 2-3 minutes. Check your Actions tab to watch the progress.");
        } else {
            const err = await res.json();
            throw new Error(err.message || "Failed to trigger workflow");
        }
    } catch (e) {
        alert("❌ Error: " + e.message);
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}
