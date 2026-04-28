const API_BASE = 'http://localhost:8000';

// DOM Elements
const uploadZone = document.getElementById('upload-zone');
const chooseBtn = document.getElementById('choose-btn');
const fileInput = document.getElementById('file-input');
const videosGrid = document.getElementById('videos-grid');
const videoCount = document.getElementById('video-count');
const emptyState = document.getElementById('empty-state');

// Modals
const uploadModal = document.getElementById('upload-modal');
const successModal = document.getElementById('success-modal');
const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toast-message');

// Modal Elements
const fileName = document.getElementById('file-name');
const progressFill = document.getElementById('progress-fill');
const dotUploading = document.getElementById('dot-uploading');
const dotTranscribing = document.getElementById('dot-transcribing');
const dotReady = document.getElementById('dot-ready');

// Success Modal Elements
const successLanguage = document.getElementById('success-language');
const successDuration = document.getElementById('success-duration');
const successObjects = document.getElementById('success-objects');
const closeSuccess = document.getElementById('close-success');

// Toast Function
function showToast(message, type = 'info') {
    toastMessage.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.remove('hidden');
    setTimeout(() => toast.style.opacity = '1', 10);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.classList.add('hidden'), 300);
    }, 4000);
}

// Load Videos
loadVideos();

// Event Listeners
uploadZone.addEventListener('click', () => fileInput.click());
chooseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
    }
});

uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.style.borderColor = 'var(--primary)';
});

uploadZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    uploadZone.style.borderColor = '';
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.style.borderColor = '';
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFileUpload(files[0]);
});

async function handleFileUpload(file) {
    if (!file.type.startsWith('video/')) {
        showToast('Please select a video file', 'error');
        return;
    }

    // UI Setup
    fileName.textContent = file.name;
    progressFill.style.width = '0%';
    resetSteps();
    if (dotUploading) dotUploading.classList.add('active');
    uploadModal.classList.remove('hidden');

    try {
        const formData = new FormData();
        formData.append('file', file);

        // Upload phase
        const response = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const initialData = await response.json();
        const videoId = initialData.video_id;

        // Start listening to progress via SSE
        const eventSource = new EventSource(`${API_BASE}/api/progress/${videoId}`);
        const logContainer = document.getElementById('log-container');
        logContainer.innerHTML = ''; // Clear initial message

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Progress Update:', data);

            // Update Message
            if (data.message) {
                document.getElementById('modal-title').textContent = data.message;
            }

            // Append Log Line
            if (data.new_log) {
                const logLine = document.createElement('div');
                logLine.className = 'log-line';
                
                // Color coding based on content
                if (data.new_log.startsWith('✓')) logLine.classList.add('success');
                else if (data.new_log.startsWith('[ERROR]')) logLine.classList.add('error');
                else if (data.new_log.startsWith('[INFO]')) logLine.classList.add('info');
                
                logLine.textContent = data.new_log;
                logContainer.appendChild(logLine);
                logContainer.scrollTop = logContainer.scrollHeight;
            } else if (data.logs && data.logs.length > 0) {
                // If it's the initial full state dump
                logContainer.innerHTML = '';
                data.logs.forEach(log => {
                    const logLine = document.createElement('div');
                    logLine.className = 'log-line';
                    if (log.startsWith('✓')) logLine.classList.add('success');
                    logLine.textContent = log;
                    logContainer.appendChild(logLine);
                });
                logContainer.scrollTop = logContainer.scrollHeight;
            }

            // Update Progress Bar (Weighted mapping)
            let totalProgress = 0;
            if (data.progress !== undefined) {
                if (data.stage === 'starting') {
                    totalProgress = 5;
                } else if (data.stage === 'transcribing') {
                    totalProgress = 10 + (data.progress * 0.4); // 10-50%
                } else if (data.stage === 'detecting' || data.stage === 'indexing') {
                    totalProgress = 50 + (data.progress * 0.5); // 50-100%
                } else if (data.stage === 'done' || data.status === 'completed') {
                    totalProgress = 100;
                }
                
                if (totalProgress > 0) {
                    progressFill.style.width = `${totalProgress}%`;
                }
            }

            // Update status text
            let statusText = "Processing...";
            if (data.stage === 'starting') statusText = "Initializing...";
            else if (data.stage === 'transcribing') statusText = "Transcribing with AI...";
            else if (data.stage === 'detecting') statusText = "Analyzing Objects...";
            else if (data.stage === 'indexing') statusText = "Finalizing Index...";
            else if (data.stage === 'done' || data.status === 'completed') statusText = "Ready!";
            document.getElementById('modal-status-badge').textContent = statusText;

            // Update Dots
            if (data.stage === 'starting' || data.stage === 'transcribing' || data.stage === 'detecting' || data.stage === 'indexing') {
                if (dotUploading) dotUploading.classList.add('active');
            }
            if (data.stage === 'transcribing' || data.stage === 'detecting' || data.stage === 'indexing') {
                if (dotTranscribing) dotTranscribing.classList.add('active');
            }
            if (data.stage === 'done' || data.status === 'completed' || (data.stage === 'indexing' && data.progress > 50)) {
                if (dotReady) dotReady.classList.add('active');
            }

            // Handle Completion
            if (data.stage === 'done' || data.status === 'completed') {
                eventSource.close();
                setTimeout(() => {
                    uploadModal.classList.add('hidden');
                    loadVideos();
                    showToast('Processing complete!', 'success');
                }, 1000);
            }

            // Handle Error
            if (data.status === 'failed') {
                eventSource.close();
                uploadModal.classList.add('hidden');
                showErrorPopup(data.error || 'Unknown processing error');
            }
        };

        eventSource.onerror = (err) => {
            console.error('SSE Error:', err);
            eventSource.close();
            // Don't necessarily fail here, as the task might still be running
        };

    } catch (error) {
        console.error('Upload error:', error);
        uploadModal.classList.add('hidden');
        showErrorPopup(error.message || 'Upload failed');
    } finally {
        fileInput.value = '';
    }
}

function showErrorPopup(message) {
    // Create a simple error alert if no specific modal exists
    alert(`Processing Error:\n\n${message}`);
}

function resetSteps() {
    document.querySelectorAll('.status-dot-item').forEach(dot => {
        dot.classList.remove('active');
    });
}

closeSuccess.addEventListener('click', () => {
    successModal.classList.add('hidden');
});

async function loadVideos() {
    try {
        const response = await fetch(`${API_BASE}/api/videos`);
        if (!response.ok) throw new Error('Failed to load videos');
        const data = await response.json();
        
        videoCount.textContent = data.count;
        if (data.count === 0) {
            emptyState.classList.remove('hidden');
            videosGrid.innerHTML = '';
        } else {
            emptyState.classList.add('hidden');
            renderVideos(data.videos);
        }
    } catch (error) {
        console.error('Error loading videos:', error);
    }
}

function renderVideos(videos) {
    videosGrid.innerHTML = '';
    videos.forEach(video => {
        const card = document.createElement('div');
        card.className = 'glass video-card';
        
        const date = new Date(video.created_at).toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric'
        });
        
        card.innerHTML = `
            <div class="video-thumbnail" style="position: relative; overflow: hidden;">
                <img src="${API_BASE}/api/thumbnail/${video.video_id}" 
                     onerror="this.style.display='none';" 
                     style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 1;"
                     alt="${video.original_name} thumbnail" />
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="position: relative; z-index: 0;">
                    <path d="M23 7l-7 5 7 5V7z"></path>
                    <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
                </svg>
                <div class="duration-tag">${formatDuration(video.duration)}</div>
            </div>
            <div class="video-info">
                <div class="video-name">${video.original_name}</div>
                <div class="video-meta">
                    <div class="video-meta-item">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                            <line x1="16" y1="2" x2="16" y2="6"></line>
                            <line x1="3" y1="10" x2="21" y2="10"></line>
                        </svg>
                        ${date}
                    </div>
                </div>
                <div class="video-actions">
                    <button class="action-btn" onclick="window.location.href='search.html?id=${video.video_id}'">
                        Search
                    </button>
                    <button class="action-btn delete" onclick="deleteVideo('${video.video_id}')">
                        Delete
                    </button>
                </div>
            </div>
        `;
        videosGrid.appendChild(card);
    });
}

async function deleteVideo(videoId) {
    if (!confirm('Permanent delete?')) return;
    try {
        const response = await fetch(`${API_BASE}/api/video/${videoId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Delete failed');
        showToast('Video removed', 'success');
        loadVideos();
    } catch (error) {
        showToast('Error deleting video', 'error');
    }
}

function formatDuration(seconds) {
    if (!seconds) return '0:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return h > 0 ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}` : `${m}:${s.toString().padStart(2, '0')}`;
}
