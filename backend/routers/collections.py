from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database.core import get_db
from database.service import get_collection_stats, get_videos_by_collection

router = APIRouter(prefix="/api")

@router.get("/collections")
async def collections_endpoint(db: Session = Depends(get_db)):
    """
    Get all smart collections and their statistics.
    """
    return get_collection_stats(db)

@router.get("/collections/{category}/{value}")
async def videos_by_collection_endpoint(
    category: str,
    value: str,
    db: Session = Depends(get_db)
):
    """
    Get all videos in a specific collection.
    """
    videos = get_videos_by_collection(db, category, value)
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
