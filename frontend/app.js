// ⚠️ Local dev only — never commit a real key here
const API_KEY = "change_me_in_production";
const BASE = "http://localhost:8000/api/v1";

// DOM Elements
const body = document.body;
const themeSwitch = document.getElementById('theme-switch');
const mainContent = document.getElementById('main-content');
const dropZone = document.getElementById('drop-zone');
const dropZoneText = document.getElementById('drop-zone-text');
const fileInput = document.getElementById('file-input');
const sourceLang = document.getElementById('source-lang');
const targetLang = document.getElementById('target-lang');
const btnProcess = document.getElementById('btn-process');
const btnProcessAnother = document.getElementById('btn-process-another');
const btnTryAgain = document.getElementById('btn-try-again');
const errorCard = document.getElementById('error-card');
const errorMessage = document.getElementById('error-message');
const uploadSection = document.getElementById('upload-section');
const pipelineSection = document.getElementById('pipeline-section');
const resultsSection = document.getElementById('results-section');
const statusText = document.getElementById('status-text');
const nodeWrappers = document.querySelectorAll('.node-wrapper');

// Result Elements
const transcriptContent = document.getElementById('transcript-content');
const srtContent = document.getElementById('srt-content');
const summaryContent = document.getElementById('summary-content');
const btnDownloadSrt = document.getElementById('btn-download-srt');
const copyButtons = document.querySelectorAll('.copy-btn');

// Allowed types
const ACCEPTED_TYPES = ['.mp4', '.mkv', '.mov', '.avi', '.webm'];

let selectedFile = null;
let currentJobId = null;
let pollTimeoutId = null;
let pollStartTime = null;
const MAX_POLL_TIME_MS = 10 * 60 * 1000; // 10 minutes

// 1. Theme
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        body.setAttribute('data-theme', 'dark');
        themeSwitch.checked = true;
    } else {
        body.setAttribute('data-theme', 'light');
    }

    themeSwitch.addEventListener('change', (e) => {
        if (e.target.checked) {
            body.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            body.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
    });
}

// 2. Upload & Validation
function initUpload() {
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
}

function handleFileSelect(file) {
    const fileName = file.name;
    const extension = fileName.substring(fileName.lastIndexOf('.')).toLowerCase();
    
    if (!ACCEPTED_TYPES.includes(extension)) {
        showError("Only video files are supported (.mp4, .mkv, .mov, .avi, .webm)");
        selectedFile = null;
        dropZoneText.textContent = "Drop video here, or click to browse";
        btnProcess.disabled = true;
        return;
    }

    selectedFile = file;
    dropZoneText.textContent = fileName;
    btnProcess.disabled = false;
    errorCard.classList.add('hidden'); // clear previous errors
}

// 4. UI State Machine
function setState(state) {
    // Hide all sections first
    errorCard.classList.add('hidden');
    uploadSection.classList.add('hidden');
    pipelineSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    btnProcess.disabled = false;
    btnProcess.textContent = "Process video";

    switch(state) {
        case 'idle':
            uploadSection.classList.remove('hidden');
            if (!selectedFile) btnProcess.disabled = true;
            resetTracker();
            break;
        case 'uploading':
            uploadSection.classList.remove('hidden');
            btnProcess.disabled = true;
            btnProcess.textContent = "Uploading...";
            break;
        case 'processing':
            pipelineSection.classList.remove('hidden');
            break;
        case 'done':
            resultsSection.classList.remove('hidden');
            break;
        case 'error':
            errorCard.classList.remove('hidden');
            uploadSection.classList.remove('hidden');
            break;
    }
}

function showError(msg) {
    errorMessage.textContent = msg;
    setState('error');
}

// Tracker UI updates
function resetTracker() {
    nodeWrappers.forEach(node => {
        node.classList.remove('active', 'done');
    });
    statusText.textContent = "Starting pipeline...";
}

function updateTrackerStage(progress) {
    // Map progress to the 7 stages linearly or specifically based on backend progress integers
    // Backend reports: 5 (Validate), 15 (Extract), 35 (VAD), 55 (STT), 75 (Export/Translate), 90 (Analyze), 100 (Done)
    let currentStageIndex = 0;
    if (progress >= 100) currentStageIndex = 7;
    else if (progress >= 90) currentStageIndex = 6; // Analyze
    else if (progress >= 70) currentStageIndex = 5; // Translate
    else if (progress >= 60) currentStageIndex = 4; // Export (happens with translate stage technically)
    else if (progress >= 35) currentStageIndex = 3; // Transcribe
    else if (progress >= 15) currentStageIndex = 2; // VAD
    else if (progress >= 5)  currentStageIndex = 1; // Extract
    else if (progress > 0)   currentStageIndex = 0; // Validate

    nodeWrappers.forEach((node, idx) => {
        node.classList.remove('active', 'done');
        if (idx < currentStageIndex) {
            node.classList.add('done');
        } else if (idx === currentStageIndex) {
            node.classList.add('active');
            const label = node.querySelector('.node-label').textContent;
            statusText.textContent = `Stage ${idx + 1} of 7 · ${capitalize(label)}ing…`;
        }
    });

    if (progress >= 100) {
        statusText.textContent = `Completed 7 of 7 stages.`;
    }
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// 3. API Integration
async function startProcess() {
    if (!selectedFile) return;

    setState('uploading');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('source_lang', sourceLang.value);
    formData.append('target_lang', targetLang.value);

    try {
        const response = await fetch(`${BASE}/process`, {
            method: 'POST',
            headers: {
                'X-API-Key': API_KEY
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }

        const data = await response.json();
        currentJobId = data.job_id;
        
        setState('processing');
        pollStartTime = Date.now();
        pollStatus(currentJobId, 0);

    } catch (err) {
        console.error(err);
        showError("Couldn't reach the server. Is the backend running on port 8000?");
    }
}

function pollStatus(jobId, retryCount) {
    if (Date.now() - pollStartTime > MAX_POLL_TIME_MS) {
        showError("This is taking longer than expected. Check the backend logs.");
        return;
    }

    pollTimeoutId = setTimeout(async () => {
        try {
            const response = await fetch(`${BASE}/status/${jobId}`, {
                headers: { 'X-API-Key': API_KEY }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            updateTrackerStage(data.progress);

            if (data.status === 'failed') {
                showError(`Processing failed: ${data.error_message || "Unknown error from API"}`);
                return;
            }

            if (data.status === 'completed') {
                renderResults(data.result);
                setState('done');
                return;
            }

            // Still processing, poll again
            pollStatus(jobId, 0);

        } catch (err) {
            console.error("Poll error:", err);
            if (retryCount < 3) {
                statusText.textContent = "Lost connection to server. Retrying…";
                pollStatus(jobId, retryCount + 1);
            } else {
                showError("Lost connection to server after multiple retries.");
            }
        }
    }, 2000);
}

// Rendering Results
function renderResults(result) {
    if (!result) return;

    transcriptContent.value = result.transcripts?.source || "No transcript available.";
    srtContent.value = result.srt_output || "No SRT available.";
    
    // Render summary paragraphs
    summaryContent.innerHTML = '';
    
    if (result.analysis?.short_summary) {
        const pShort = document.createElement('p');
        pShort.innerHTML = `<strong>Summary:</strong> ${result.analysis.short_summary}`;
        summaryContent.appendChild(pShort);
    }

    if (result.analysis?.detailed_points && Array.isArray(result.analysis.detailed_points)) {
        result.analysis.detailed_points.forEach((point, i) => {
            const pDetail = document.createElement('p');
            pDetail.textContent = `${i + 1}. ${point}`;
            summaryContent.appendChild(pDetail);
        });
    }

    // Prepare SRT download blob
    if (result.srt_output) {
        btnDownloadSrt.onclick = () => {
            const blob = new Blob([result.srt_output], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `substudy_${currentJobId}.srt`;
            a.click();
            URL.revokeObjectURL(url);
        };
    }
}

// Copy to Clipboard
copyButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-target');
        const targetEl = document.getElementById(targetId);
        
        let textToCopy = '';
        if (targetEl.tagName === 'TEXTAREA') {
            textToCopy = targetEl.value;
        } else {
            textToCopy = targetEl.innerText;
        }

        navigator.clipboard.writeText(textToCopy).then(() => {
            const originalIcon = btn.innerText;
            btn.innerText = '✅';
            setTimeout(() => btn.innerText = originalIcon, 2000);
        });
    });
});

// Initialization & Event Binding
btnProcess.addEventListener('click', startProcess);
btnTryAgain.addEventListener('click', () => setState('idle'));
btnProcessAnother.addEventListener('click', () => {
    selectedFile = null;
    dropZoneText.textContent = "Drop video here, or click to browse";
    fileInput.value = '';
    setState('idle');
});

initTheme();
initUpload();
setState('idle');
