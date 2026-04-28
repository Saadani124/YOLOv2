# VideoVault - Dual Interface System

## Overview

Your VideoVault application now has **two separate interfaces**:

1. **Admin Interface** (`admin.html`) - For uploading and managing videos
2. **Search Interface** (`search.html`) - For users to search within videos

Both interfaces feature a clean **olive green theme** inspired by your reference designs.

---

## File Structure

```
frontend/
├── admin.html          # Admin panel for video uploads
├── admin-style.css     # Olive green styling for admin
├── admin.js            # Admin upload & management logic
├── search.html         # User search interface
├── search-style.css    # Olive green styling for search
└── search.js           # Search functionality logic
```

---

## Installation

1. **Copy all 6 files** to your `frontend/` directory (or wherever your frontend files are served from)

2. **Update your backend** to serve these files:
   - Make sure your FastAPI app serves static files from the frontend directory
   - The backend API should remain at `http://localhost:8000`

3. **Start your backend server**:
   ```bash
   python run.py
   ```

4. **Access the interfaces**:
   - Admin Panel: `http://localhost:8000/admin.html`
   - Search Page: `http://localhost:8000/search.html`

---

## Admin Interface Features

### Upload & Index Video
- Drag & drop or click to upload video files
- Real-time upload progress with 4 steps:
  1. **Uploading** - File transfer to server
  2. **Transcribing** - AI speech-to-text processing
  3. **Speaker ID** - Diarization (speaker identification)
  4. **Indexing** - Storing in database

### Success Modal
After successful upload, displays:
- Language detected
- Video duration
- Number of segments
- Number of speakers

### Video Management
- View all indexed videos in a grid
- Each card shows:
  - Video name
  - Duration and upload date
  - Segment count
  - Speaker count
  - Language
- Delete videos with confirmation

### Navigation
- Switch between Admin and Search interfaces via top navigation

---

## Search Interface Features

### Video Selection
- Clean hero section with "Find Any Moment" heading
- Dropdown to select from all indexed videos
- Shows video duration in dropdown

### Search Functionality
Once a video is selected:
- Video info displayed (duration, language, speaker count)
- Search bar for entering queries
- Video player appears when search is performed
- Click results to jump to that moment in the video

### Search Results
Each result shows:
- Timestamp
- Speaker label (if diarization enabled)
- Match type badge (Exact, Fuzzy, Partial, All Words)
- Match score percentage
- Highlighted query in text
- Click to jump to that moment

### Navigation
- "Change Video" button to go back to video selection
- Switch to Admin panel via top navigation

---

## Theme Customization

The olive green theme uses these main colors:

```css
--primary: #6b7c3a;           /* Main olive green */
--accent-orange: #d97d3a;     /* Orange accent (buttons) */
--bg-primary: #1a1d16;        /* Dark background */
--text-primary: #f5f5f0;      /* Light text */
```

To customize colors, edit the `:root` variables in:
- `admin-style.css` (lines 11-32)
- `search-style.css` (lines 11-32)

---

## Backend Requirements

Your backend should have these endpoints (already implemented):

### Upload
- `POST /api/upload` - Upload and process video

### Video Management
- `GET /api/videos` - Get list of all videos
- `GET /api/video/{video_id}` - Stream video file
- `DELETE /api/video/{video_id}` - Delete video
- `GET /api/transcript/{video_id}` - Get full transcript

### Search
- `POST /api/search` - Search within video
  - Body: `{ "video_id": "...", "query": "..." }`

---

## Features Comparison

| Feature | Admin | Search |
|---------|-------|--------|
| Upload videos | ✅ | ❌ |
| Delete videos | ✅ | ❌ |
| View all videos | ✅ | ✅ |
| Search transcripts | ❌ | ✅ |
| Play videos | ❌ | ✅ |
| Jump to moments | ❌ | ✅ |

---

## User Flow

### Admin Workflow
1. Navigate to `admin.html`
2. Upload video via drag-drop or file picker
3. Wait for processing (upload → transcribe → diarize → index)
4. View success message with video details
5. See video appear in "Indexed Videos" grid
6. Optionally delete videos

### User Workflow
1. Navigate to `search.html`
2. Select a video from dropdown
3. Enter search query (dialogue, keywords, etc.)
4. Click "SEARCH"
5. Browse results with timestamps and speaker labels
6. Click result to jump to that moment in video
7. Optionally search again or change video

---

## Troubleshooting

### Videos not loading in dropdown
- Check that backend is running: `http://localhost:8000/health`
- Check `/api/videos` endpoint returns data
- Look for CORS errors in browser console

### Upload failing
- Ensure file is under 500MB
- Check backend logs for errors
- Verify ffmpeg is installed: `pip install imageio-ffmpeg`
- Check database connection in backend

### Search not working
- Verify video is selected before searching
- Check browser console for API errors
- Ensure `/api/search` endpoint is working
- Check if query is not empty

### Styling issues
- Clear browser cache
- Check that CSS files are being loaded
- Verify paths in HTML `<link>` tags
- Look for console errors

---

## Next Steps

### Optional Enhancements
1. **Authentication**: Add login for admin panel
2. **Permissions**: Restrict admin access
3. **Thumbnails**: Generate video thumbnails
4. **Filters**: Filter videos by language, date, speaker count
5. **Batch Upload**: Upload multiple videos at once
6. **Export**: Export search results or transcripts
7. **Analytics**: Track popular searches
8. **Sharing**: Share specific moments via URLs

---

## Support

For issues or questions:
1. Check browser console for errors
2. Check backend logs
3. Verify all files are in the correct directory
4. Ensure backend API is accessible

---

**Enjoy your new VideoVault dual-interface system! 🎥🔍**
