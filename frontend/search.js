const API_BASE = 'http://localhost:8000';

// DOM Elements
const selectionView = document.getElementById('selection-view');
const searchView = document.getElementById('search-view');
const videoDropdown = document.getElementById('video-dropdown');
const backBtn = document.getElementById('back-btn');

// Search Elements
const searchInput = document.getElementById('search-input');
const resultsList = document.getElementById('results-list');
const resultsCount = document.getElementById('results-count');
const tabBtns = document.querySelectorAll('.tab-btn');

// Transcript Elements
const transcriptCollapsible = document.querySelector('.transcript-collapsible');
const transcriptTrigger = document.getElementById('transcript-trigger');
const fullTranscriptContent = document.getElementById('full-transcript-content');
const triggerText = document.getElementById('trigger-text');

// Filter Elements
const filterTagsSection = document.getElementById('filter-tags-section');
const filterTagsContainer = document.getElementById('filter-tags-container');

// Player Elements
const videoPlayer = document.getElementById('video-player');
const currentVideoName = document.getElementById('current-video-name');

// Timeline Elements
const timelineContainer = document.getElementById('timeline-container');
const layerTranscript = document.getElementById('layer-transcript');
const layerObjects = document.getElementById('layer-objects');
const layerVisualText = document.getElementById('layer-visual-text');
const timelinePlayhead = document.getElementById('timeline-playhead');
const currentTimeDisplay = document.getElementById('current-time');
const totalTimeDisplay = document.getElementById('total-time');

// State
let currentId = null;
let activeTab = 'transcript';
let videos = [];
let fullTranscriptData = null;

// Init
loadVideoList();

// Event Listeners
videoDropdown.addEventListener('change', (e) => {
    if (e.target.value) switchVideo(e.target.value);
});

backBtn.addEventListener('click', () => {
    searchView.classList.add('hidden');
    selectionView.classList.remove('hidden');
    videoPlayer.src = '';
    currentId = null;
    fullTranscriptData = null;
    transcriptCollapsible.classList.remove('open');
    fullTranscriptContent.classList.add('hidden');
    triggerText.textContent = 'Show Full Transcript';
});

transcriptTrigger.addEventListener('click', () => {
    transcriptCollapsible.classList.toggle('open');
    fullTranscriptContent.classList.toggle('hidden');
    
    const isOpen = !fullTranscriptContent.classList.contains('hidden');
    triggerText.textContent = isOpen ? 'Hide Full Transcript' : 'Show Full Transcript';
    
    if (isOpen && !fullTranscriptData) {
        loadFullTranscript();
    }
});

tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeTab = btn.dataset.tab;
        
        if (activeTab === 'objects') {
            searchInput.placeholder = "Search for an object...";
        } else {
            searchInput.placeholder = "What are you looking for?";
        }
        
        loadFilterTags();
        performSearch();
    });
});

// Update input on debounced search for live feel
searchInput.addEventListener('input', debounce(performSearch, 350));

// Timeline Interaction via Event Delegation
timelineContainer.addEventListener('click', (e) => {
    if (!videoPlayer.duration) return;
    
    const marker = e.target.closest('.timeline-marker');
    if (marker && marker.dataset.start) {
        videoPlayer.currentTime = parseFloat(marker.dataset.start);
        return;
    }
    
    const rect = timelineContainer.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = x / rect.width;
    videoPlayer.currentTime = percentage * videoPlayer.duration;
});

// Transcript Interaction via Event Delegation
fullTranscriptContent.addEventListener('click', (e) => {
    if (e.target.classList.contains('time-badge') && e.target.dataset.start) {
        videoPlayer.currentTime = parseFloat(e.target.dataset.start);
        videoPlayer.play();
    }
});

// Throttle timeupdate to ~10 fps to avoid per-frame DOM reflows
let _lastTimeUpdate = 0;
videoPlayer.addEventListener('timeupdate', () => {
    const now = performance.now();
    if (now - _lastTimeUpdate < 100) return; // ~10fps
    _lastTimeUpdate = now;
    if (!videoPlayer.duration) return;
    const percentage = (videoPlayer.currentTime / videoPlayer.duration) * 100;
    timelinePlayhead.style.left = `${percentage}%`;
    currentTimeDisplay.textContent = formatDuration(videoPlayer.currentTime);
});

videoPlayer.addEventListener('loadedmetadata', () => {
    totalTimeDisplay.textContent = formatDuration(videoPlayer.duration);
});

async function loadVideoList() {
    try {
        const res = await fetch(`${API_BASE}/api/videos`);
        const data = await res.json();
        videos = data.videos;
        
        videoDropdown.innerHTML = '<option value="">Select a video to begin searching...</option>';
        videos.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v.video_id;
            opt.textContent = `${v.original_name} (${formatDuration(v.duration)})`;
            videoDropdown.appendChild(opt);
        });
        
        // Handle URL param if exists
        const urlParams = new URLSearchParams(window.location.search);
        const id = urlParams.get('id');
        if (id) switchVideo(id);

    } catch (e) {
        console.error('Failed to load videos', e);
    }
}

async function switchVideo(id) {
    currentId = id;
    const video = videos.find(v => v.video_id === id);
    if (!video) {
        try {
            const res = await fetch(`${API_BASE}/api/videos`);
            const data = await res.json();
            videos = data.videos;
            const v2 = videos.find(v => v.video_id === id);
            if (v2) updateUIWithVideo(v2);
        } catch (e) {}
    } else {
        updateUIWithVideo(video);
    }
}

function updateUIWithVideo(video) {
    currentVideoName.textContent = video.original_name;
    videoPlayer.src = `${API_BASE}/api/video/${video.video_id}`;
    selectionView.classList.add('hidden');
    searchView.classList.remove('hidden');
    
    // Reset Transcript
    fullTranscriptData = null;
    fullTranscriptContent.innerHTML = '<div class="transcript-loading">Loading transcript...</div>';
    
    // Clear and Initial Timeline Load
    layerTranscript.innerHTML = '';
    layerObjects.innerHTML = '';
    if (layerVisualText) layerVisualText.innerHTML = '';
    initTimelineData(video.video_id);
    
    // Initial search and filters
    loadFilterTags();
    performSearch();
    searchInput.focus();
}

async function loadFullTranscript() {
    if (!currentId) return;
    try {
        const res = await fetch(`${API_BASE}/api/transcript/${currentId}`);
        const data = await res.json();
        fullTranscriptData = data.segments;
        renderFullTranscript(data.segments);
    } catch (e) {
        fullTranscriptContent.innerHTML = '<div class="error">Failed to load transcript.</div>';
    }
}

function renderFullTranscript(segments) {
    let html = '<div class="transcript-p">';
    
    segments.forEach(seg => {
        html += `<span class="transcript-segment-inline">` + 
                `<span class="time-badge" data-start="${seg.start}">[${seg.start_formatted}]</span>` + 
                ` ${seg.text} </span>`;
    });
    
    html += '</div>';
    fullTranscriptContent.innerHTML = html;
}

async function initTimelineData(videoId) {
    try {
        // Fire requests in parallel
        const [transRes, objRes, textRes] = await Promise.all([
            fetch(`${API_BASE}/api/transcript/${videoId}`),
            fetch(`${API_BASE}/api/search/objects`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ video_id: videoId, query: '' })
            }),
            fetch(`${API_BASE}/api/search/visual-text`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ video_id: videoId, query: '' })
            })
        ]);
        const [transData, objData, textData] = await Promise.all([transRes.json(), objRes.json(), textRes.json()]);

        renderTimelineMarkers(transData.segments, layerTranscript, 'transcript');
        renderTimelineMarkers(objData.results, layerObjects, 'object');
        if (layerVisualText && textData.results) {
            renderTimelineMarkers(textData.results, layerVisualText, 'visual-text');
        }
    } catch (e) {
        console.error('Failed to init timeline data', e);
    }
}

function renderTimelineMarkers(data, container, type) {
    if (!videoPlayer.duration && !videos.find(v => v.video_id === currentId)?.duration) return;
    const duration = videoPlayer.duration || videos.find(v => v.video_id === currentId).duration;
    
    let html = '';
    data.forEach(item => {
        const start = item.start || item.start_time;
        const end = item.end || item.end_time || (start + 0.5);
        const left = (start / duration) * 100;
        const width = ((end - start) / duration) * 100;
        
        html += `<div class="timeline-marker ${type}" style="left: ${left}%; width: ${Math.max(width, 0.2)}%;" data-start="${start}"></div>`;
    });
    container.innerHTML = html;
}

async function performSearch() {
    const query = searchInput.value.trim();
    if (!currentId) return;

    // Show loading state if needed
    if (query) {
        resultsCount.textContent = 'Searching...';
    } else {
        resultsCount.textContent = 'Loading all...';
    }

    try {
        let endpoint = '/api/search';
        if (activeTab === 'objects') endpoint = '/api/search/objects';
        else if (activeTab === 'visual-text') endpoint = '/api/search/visual-text';

        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_id: currentId, query: query })
        });
        
        const data = await res.json();
        renderResults(data.results, query);
        highlightTimelineMatches(data.results);
    } catch (e) {
        console.error('Search error', e);
    }
}

function highlightTimelineMatches(results) {
    // Clear active classes quickly
    const activeMarkers = document.querySelectorAll('.timeline-marker.active');
    activeMarkers.forEach(m => m.classList.remove('active'));

    if (!results || results.length === 0 || !videoPlayer.duration) return;

    // Build O(1) lookup Map for marker times rounded to nearest 0.1s
    const markers = document.querySelectorAll('.timeline-marker');
    const markersByTime = new Map();
    
    markers.forEach(m => {
        const start = parseFloat(m.dataset.start);
        if (isNaN(start)) return;
        
        const t = Math.round(start * 10);
        if (!markersByTime.has(t)) markersByTime.set(t, []);
        markersByTime.get(t).push(m);
    });

    // Apply active classes using Map lookup (O(N) instead of O(N*M))
    results.forEach(res => {
        const start = res.start || res.start_time;
        const t = Math.round(start * 10);
        
        for (let dt = -1; dt <= 1; dt++) {
            const match = markersByTime.get(t + dt);
            if (match) match.forEach(m => m.classList.add('active'));
        }
    });
}

async function loadFilterTags() {
    if (!currentId) return;
    
    try {
        let endpoint = `/api/keywords/${currentId}`;
        if (activeTab === 'objects') endpoint = `/api/objects/${currentId}`;
        else if (activeTab === 'visual-text') endpoint = `/api/visual-text/${currentId}`;
        
        const res = await fetch(`${API_BASE}${endpoint}`);
        const data = await res.json();
        
        let items = data.keywords;
        if (activeTab === 'objects') items = data.objects;
        else if (activeTab === 'visual-text') items = data.words;
        
        renderFilterTags(items);
    } catch (e) {
        console.error('Failed to load filter tags', e);
        filterTagsSection.classList.add('hidden');
    }
}

function renderFilterTags(items) {
    filterTagsContainer.innerHTML = '';
    
    if (!items || items.length === 0) {
        filterTagsSection.classList.add('hidden');
        return;
    }
    
    filterTagsSection.classList.remove('hidden');
    
    // Show up to 30 tags
    items.slice(0, 30).forEach(item => {
        const text = item.object_class || item.word;
        const count = item.count;
        
        const tag = document.createElement('div');
        tag.className = 'filter-tag';
        if (searchInput.value.toLowerCase() === text.toLowerCase()) {
            tag.classList.add('active');
        }
        
        tag.innerHTML = `
            <span>${text}</span>
            <span class="tag-count">${count}</span>
        `;
        
        tag.onclick = () => {
            if (searchInput.value === text) {
                searchInput.value = '';
            } else {
                searchInput.value = text;
            }
            
            // Update active state
            document.querySelectorAll('.filter-tag').forEach(t => t.classList.remove('active'));
            if (searchInput.value === text) tag.classList.add('active');
            
            performSearch();
        };
        
        filterTagsContainer.appendChild(tag);
    });
}

function renderResults(results, query) {
    if (!results || results.length === 0) {
        resultsList.innerHTML = '<div style="text-align: center; padding: 3rem 1rem; color: var(--text-muted);">No matches found</div>';
        resultsCount.textContent = '0 found';
        return;
    }

    resultsCount.textContent = `${results.length} found`;
    resultsList.innerHTML = '';
    
    results.forEach(res => {
        const item = document.createElement('div');
        item.className = 'result-item';
        
        const time = res.start_formatted || res.timestamp_formatted || formatDuration(res.start || res.start_time);
        let text = '';
        
        if (activeTab === 'transcript') {
            text = highlight(res.text, query);
        } else if (activeTab === 'objects') {
            text = `Detected <b>${res.object_class}</b> (Confidence: ${res.confidence}%)`;
        }

        item.innerHTML = `
            <span class="result-time">${time}</span>
            <div class="result-text">${text}</div>
        `;
        
        item.onclick = () => {
            videoPlayer.currentTime = res.start || res.start_time || res.timestamp || 0;
            videoPlayer.play();
        };
        
        resultsList.appendChild(item);
    });
}

function highlight(text, query) {
    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

function formatDuration(seconds) {
    if (!seconds) return '0:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return h > 0 ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}` : `${m}:${s.toString().padStart(2, '0')}`;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
