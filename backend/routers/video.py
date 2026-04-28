import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database.core import get_db
from database.service import get_video, get_all_videos, delete_video
from config import UPLOAD_DIR, ALLOWED_VIDEO_EXTENSIONS
from core.utils import get_file_extension
from services.ffmpeg import is_ffmpeg_available
from core.progress import progress_manager
from tasks.background import process_video_background

router = APIRouter(prefix="/api")

@router.post("/upload")
async def upload_video_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    ext = get_file_extension(file.filename)
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'.")
    if not is_ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg is not installed.")

    video_id = str(uuid.uuid4())
    video_filename = f"{video_id}{ext}"
    video_path = os.path.join(UPLOAD_DIR, video_filename)

    try:
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = os.path.getsize(video_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    progress_manager.start_task(video_id, f"Uploaded {file.filename}")
    background_tasks.add_task(
        process_video_background,
        video_id=video_id,
        video_path=video_path,
        video_filename=video_filename,
        original_name=file.filename,
        file_size=file_size
    )

    return {
        "video_id": video_id,
        "message": "Upload successful. Processing started in background.",
        "status_url": f"/api/progress/{video_id}"
    }

@router.get("/video/{video_id}")
async def get_video_stream(video_id: str, db: Session = Depends(get_db)):
    video = get_video(db, video_id)
    if not video or not os.path.exists(video.file_path):
        raise HTTPException(status_code=404, detail="Video file not found.")
    return FileResponse(video.file_path, media_type="video/mp4", headers={"Accept-Ranges": "bytes"})

@router.get("/thumbnail/{video_id}")
async def get_video_thumbnail(video_id: str):
    thumbnail_path = os.path.join(UPLOAD_DIR, f"{video_id}.jpg")
    if not os.path.exists(thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found.")
    return FileResponse(thumbnail_path, media_type="image/jpeg")

@router.get("/videos")
async def list_videos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    videos = get_all_videos(db, skip=skip, limit=limit)
    return {
        "count": len(videos),
        "videos": [
            {
                "video_id": v.video_id,
                "original_name": v.original_name,
                "language": v.language,
                "duration": v.duration,
                "created_at": v.created_at.isoformat(),
                "segment_count": len(v.segments),
            }
            for v in videos
        ]
    }

@router.delete("/video/{video_id}")
async def delete_video_endpoint(video_id: str, db: Session = Depends(get_db)):
    video = get_video(db, video_id)
    if not video: raise HTTPException(status_code=404, detail="Video not found.")
    
    if os.path.exists(video.file_path):
        try:
            os.remove(video.file_path)
        except Exception as e:
            print(f"Warning: Could not delete file {video.file_path}: {e}")
            
    delete_video(db, video_id)
    return {"message": f"Video {video_id} deleted successfully"}
