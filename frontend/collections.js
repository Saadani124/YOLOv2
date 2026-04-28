const API_BASE = 'http://localhost:8000';

// DOM Elements
const container = document.getElementById('collections-container');
const overlay = document.getElementById('collection-overlay');
const overlayTitle = document.getElementById('overlay-title');
const overlaySubtitle = document.getElementById('overlay-subtitle');
const videoGridOverlay = document.getElementById('video-grid-overlay');
const closeOverlayBtn = document.getElementById('close-overlay');

// Init
loadCollections();

closeOverlayBtn.onclick = () => {
    overlay.style.display = 'none';
    document.body.style.overflow = 'auto';
};

async function loadCollections() {
    try {
        const res = await fetch(`${API_BASE}/api/collections`);
        const data = await res.json();
        renderCollections(data);
    } catch (e) {
        console.error('Failed to load collections', e);
        container.innerHTML = '<div style="text-align: center; padding: 5rem; color: #e74c3c;"><p>Failed to load collections. Please check the server.</p></div>';
    }
}

function renderCollections(data) {
    container.innerHTML = '';

    const categories = [
        { id: 'languages', title: 'Languages', icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 0 1-9 9m9-9a9 9 0 0 0-9-9m9 9H3m9 9a9 9 0 0 1-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 0 1 9-9"></path></svg>' },
        { id: 'objects', title: 'Objects Detected', icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M12 8v4l3 3"></path></svg>' },
        { id: 'visual_text', title: 'On-Screen Keywords', icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>' }
    ];

    categories.forEach(cat => {
        const items = data[cat.id];
        if (!items || items.length === 0) return;

        const section = document.createElement('div');
        section.innerHTML = `<h2 class="category-title">${cat.title}</h2>`;
        
        const grid = document.createElement('div');
        grid.className = 'collections-grid';
        
        items.forEach(item => {
            const card = document.createElement('div');
            card.className = 'collection-card';
            card.innerHTML = `
                <div class="collection-icon">${cat.icon}</div>
                <div class="collection-name">${item.value}</div>
                <div class="collection-count">${item.count} ${item.count === 1 ? 'video' : 'videos'}</div>
            `;
            
            card.onclick = () => showCollectionVideos(cat.id.replace('s', '').replace('_text', ''), item.value);
            grid.appendChild(card);
        });
        
        section.appendChild(grid);
        container.appendChild(section);
    });
}

async function showCollectionVideos(category, value) {
    overlay.style.display = 'block';
    document.body.style.overflow = 'hidden';
    overlayTitle.textContent = value;
    overlaySubtitle.textContent = 'Loading videos...';
    videoGridOverlay.innerHTML = '<div class="spinner" style="grid-column: 1/-1; margin: 5rem auto;"></div>';

    try {
        const res = await fetch(`${API_BASE}/api/collections/${category}/${value}`);
        const data = await res.json();
        
        overlaySubtitle.textContent = `${data.count} ${data.count === 1 ? 'video' : 'videos'} in this collection`;
        videoGridOverlay.innerHTML = '';
        
        data.videos.forEach(v => {
            const card = document.createElement('div');
            card.className = 'video-card-mini';
            card.innerHTML = `
                <img class="card-thumb" src="${API_BASE}/api/thumbnail/${v.video_id}" onerror="this.src='https://via.placeholder.com/320x180?text=No+Thumb'">
                <div class="card-info">
                    <div class="card-title">${v.original_name}</div>
                    <div class="card-meta">${formatDuration(v.duration)} • ${v.language.toUpperCase()}</div>
                </div>
            `;
            
            card.onclick = () => window.location.href = `search.html?id=${v.video_id}`;
            videoGridOverlay.appendChild(card);
        });
    } catch (e) {
        console.error('Failed to load collection videos', e);
        videoGridOverlay.innerHTML = '<p style="color: #e74c3c;">Failed to load videos.</p>';
    }
}

function formatDuration(seconds) {
    if (!seconds) return '0:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return h > 0 ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}` : `${m}:${s.toString().padStart(2, '0')}`;
}
