const API_BASE = 'http://localhost:8000';

// DOM Elements
const searchInput = document.getElementById('global-search-input');
const resultsContainer = document.getElementById('global-results-container');
const resultsCountDisplay = document.getElementById('results-count-global');

// State
let lastQuery = '';

// Init
searchInput.addEventListener('input', debounce(performGlobalSearch, 500));

async function performGlobalSearch() {
    const query = searchInput.value.trim();
    if (query === lastQuery) return;
    
    if (query.length < 2) {
        resultsContainer.innerHTML = `
            <div class="empty-state-global">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 1rem; opacity: 0.5;">
                    <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                </svg>
                <p>Enter at least 2 characters to search</p>
            </div>
        `;
        resultsCountDisplay.textContent = '';
        return;
    }

    lastQuery = query;
    
    // Show loading
    resultsContainer.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    resultsCountDisplay.textContent = 'Searching across library...';

    try {
        const res = await fetch(`${API_BASE}/api/search/global`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        
        const data = await res.json();
        renderGlobalResults(data, query);
    } catch (e) {
        console.error('Global search error', e);
        resultsContainer.innerHTML = '<div class="empty-state-global"><p style="color: #e74c3c;">Search failed. Please check if the server is running.</p></div>';
        resultsCountDisplay.textContent = '';
    }
}

function renderGlobalResults(data, query) {
    if (!data.video_results || data.video_results.length === 0) {
        resultsContainer.innerHTML = `
            <div class="empty-state-global">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 1rem; opacity: 0.5;">
                    <path d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p>No matches found for "${query}" across any videos.</p>
            </div>
        `;
        resultsCountDisplay.textContent = '0 results found';
        return;
    }

    resultsCountDisplay.textContent = `Found ${data.total_matches} matches across ${data.video_results.length} videos`;
    resultsContainer.innerHTML = '';

    data.video_results.forEach(video => {
        const videoGroup = document.createElement('div');
        videoGroup.className = 'video-result-group';
        
        const duration = formatDuration(video.duration);
        const matchCount = video.matches.length;
        
        videoGroup.innerHTML = `
            <div class="video-group-header">
                <img class="video-thumbnail-mini" src="${API_BASE}/api/thumbnail/${video.video_id}" alt="${video.video_name}" onerror="this.src='https://via.placeholder.com/160x90?text=No+Thumb'">
                <div class="video-group-info">
                    <h3 class="video-group-title">${video.video_name}</h3>
                    <div class="video-group-meta">
                        <span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 4px;"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg> ${duration}</span>
                        <span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 4px;"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg> ${matchCount} ${matchCount === 1 ? 'match' : 'matches'}</span>
                        <span style="text-transform: uppercase;">${video.language}</span>
                    </div>
                </div>
            </div>
            <div class="matches-list"></div>
        `;
        
        const matchesList = videoGroup.querySelector('.matches-list');
        
        video.matches.forEach(match => {
            const matchCard = document.createElement('div');
            matchCard.className = `match-card match-type-${match.match_type}`;
            
            const highlightedText = highlightText(match.text, query);
            const matchTypeLabel = getMatchTypeLabel(match.match_type);
            
            matchCard.innerHTML = `
                <div class="match-timestamp">${match.timestamp_formatted}</div>
                <div class="match-content">
                    <div class="match-text">${highlightedText}</div>
                    <button class="download-btn" onclick="event.stopPropagation(); downloadClip('${video.video_id}', '${match.timestamp}', '${match.timestamp + 15}')">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        Download Clip
                    </button>
                </div>
                <div class="match-type-badge">${matchTypeLabel}</div>
                <div style="color: var(--text-muted);">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M9 18l6-6-6-6"></path>
                    </svg>
                </div>
            `;
            
            matchCard.onclick = () => {
                window.location.href = `search.html?id=${video.video_id}&t=${match.timestamp}`;
            };
            
            matchesList.appendChild(matchCard);
        });
        
        resultsContainer.appendChild(videoGroup);
    });
}

function getMatchTypeLabel(type) {
    switch(type) {
        case 'transcript': return 'Dialogue';
        case 'object': return 'Object';
        case 'ocr': return 'Visual Text';
        default: return type;
    }
}

function highlightText(text, query) {
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

async function downloadClip(videoId, start, end) {
    // Show toast or some indicator
    // We don't have a toast in advanced-search.html, let's add one or use alert
    alert("Preparing your clip... please wait.");

    try {
        const url = `${API_BASE}/api/clip/${videoId}?start=${start}&end=${end}`;
        const res = await fetch(url);
        
        if (!res.ok) throw new Error('Failed to generate clip');
        
        const blob = await res.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `clip_${videoId}_${start}.mp4`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        a.remove();
    } catch (e) {
        console.error('Download error', e);
        alert("Failed to generate clip.");
    }
}
