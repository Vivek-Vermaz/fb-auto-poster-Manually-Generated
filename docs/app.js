// Automatically load config and state when page opens
document.addEventListener('DOMContentLoaded', () => {
    loadData();
});

async function loadData() {
    try {
        // Fetch from the local/gh-pages relative path
        const configRes = await fetch('config.json');
        if (configRes.ok) {
            const config = await configRes.json();
            document.getElementById('cloudinaryFolder').value = config.cloudinary_folder || '';
            document.getElementById('frequency').value = config.frequency || 6;
            document.getElementById('captions').value = (config.captions || []).join(',\n');
        }

        const stateRes = await fetch('state.json');
        if (stateRes.ok) {
            const state = await stateRes.json();
            document.getElementById('dailyCount').innerText = state.daily_count || 0;
            
            if (state.last_run) {
                const d = new Date(state.last_run);
                document.getElementById('lastRun').innerText = d.toLocaleString();
            }

            const tbody = document.querySelector('#historyTable tbody');
            tbody.innerHTML = '';
            
            (state.posted || []).forEach(post => {
                const tr = document.createElement('tr');
                const d = new Date(post.time);
                tr.innerHTML = `
                    <td>${d.toLocaleString()}</td>
                    <td><span class="badge">Success</span></td>
                    <td><a href="${post.url}" target="_blank">View Post</a></td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        console.log("Could not load local data (This is normal on first run or local file protocol): ", e);
    }
}

async function saveSettings() {
    const token = document.getElementById('ghToken').value;
    const repo = document.getElementById('ghRepo').value;
    const statusEl = document.getElementById('saveStatus');
    
    if (!token || !repo) {
        statusEl.innerText = "GitHub Token and Repo name are required to save.";
        statusEl.style.color = "red";
        return;
    }

    const captionsRaw = document.getElementById('captions').value;
    const captionsArray = captionsRaw.split(',').map(c => c.trim()).filter(c => c.length > 0);
    
    const newConfig = {
        cloudinary_folder: document.getElementById('cloudinaryFolder').value,
        frequency: parseInt(document.getElementById('frequency').value, 10),
        captions: captionsArray
    };

    statusEl.innerText = "Saving to GitHub...";
    statusEl.style.color = "orange";

    try {
        // 1. Get the current file SHA
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
        } catch (e) {
            // File might not exist yet, that's fine
        }

        // 2. Put the new file
        const contentBase64 = btoa(unescape(encodeURIComponent(JSON.stringify(newConfig, null, 2))));
        const bodyData = {
            message: "Update config via Dashboard",
            content: contentBase64
        };
        if (sha) bodyData.sha = sha;

        const putRes = await fetch(getUrl, {
            method: 'PUT',
            headers: getHeaders,
            body: JSON.stringify(bodyData)
        });

        if (putRes.ok) {
            statusEl.innerText = "✅ Successfully saved! The automation will use these settings on its next run.";
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
