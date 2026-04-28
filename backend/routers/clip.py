import os
import uuid
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database.core import get_db
from database.service import get_video
from services.ffmpeg import create_video_clip, is_ffmpeg_available
from config import UPLOAD_DIR

router = APIRouter(prefix="/api")

@router.get("/clip/{video_id}")
async def get_video_clip(
    video_id: str,
    start: float,
    end: float,
    db: Session = Depends(get_db)
):
    """
    Generate and return a video clip for a specific time range.
    """
    if not is_ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg is not installed.")

    video = get_video(db, video_id)
    if not video or not os.path.exists(video.file_path):
        raise HTTPException(status_code=404, detail="Video file not found.")

    if start < 0 or end <= start or end > video.duration + 1: # +1 for small buffer
        raise HTTPException(status_code=400, detail="Invalid time range.")

    clip_id = str(uuid.uuid4())
    clip_filename = f"clip_{clip_id}.mp4"
    clip_path = os.path.join(UPLOAD_DIR, clip_filename)

    success = create_video_clip(video.file_path, clip_path, start, end)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to generate clip.")

    # We return the file and use a background task to delete it after some time
    # (or just let it sit if we don't have a cleanup mechanism yet)
    return FileResponse(
        clip_path, 
        media_type="video/mp4", 
        filename=f"clip_{video.original_name}_{int(start)}.mp4"
    )
