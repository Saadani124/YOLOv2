from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database.core import get_db
from database.service import (
    get_video, get_segments_for_video, segment_to_dict,
    get_unique_objects_in_video, get_detections_for_video,
    get_unique_words_in_video, get_visual_texts_for_video
)
from services.text_processing import extract_keywords

router = APIRouter(prefix="/api")

@router.get("/transcript/{video_id}")
async def get_transcript_endpoint(video_id: str, db: Session = Depends(get_db)):
    video = get_video(db, video_id)
    if not video: raise HTTPException(status_code=404, detail="Video not found.")
    db_segments = get_segments_for_video(db, video_id)
    segments = [segment_to_dict(seg, include_words=True) for seg in db_segments]
    return {"video_id": video_id, "language": video.language, "full_text": video.full_text, "segments": segments}

@router.get("/objects/{video_id}")
async def get_detected_objects_endpoint(video_id: str, db: Session = Depends(get_db)):
    unique_objects = get_unique_objects_in_video(db, video_id)
    object_stats = []
    for obj_class in unique_objects:
        detections = get_detections_for_video(db, video_id, object_class=obj_class)
        object_stats.append({
            "object_class": obj_class,
            "count": len(detections),
            "avg_confidence": round(sum(d.confidence for d in detections) / len(detections), 2) if detections else 0
        })
    object_stats.sort(key=lambda x: x["count"], reverse=True)
    return {"video_id": video_id, "object_count": len(unique_objects), "objects": object_stats}

@router.get("/keywords/{video_id}")
async def get_video_keywords_endpoint(video_id: str, db: Session = Depends(get_db)):
    video = get_video(db, video_id)
    if not video: raise HTTPException(status_code=404, detail="Video not found.")
    keywords = extract_keywords(video.full_text, limit=50)
    return {"video_id": video_id, "keywords": [{"word": k[0], "count": k[1]} for k in keywords]}

@router.get("/visual-text/{video_id}")
async def get_visual_text_endpoint(video_id: str, db: Session = Depends(get_db)):
    unique_words = get_unique_words_in_video(db, video_id)
    text_stats = []
    for word in unique_words:
        texts = get_visual_texts_for_video(db, video_id, text_query=word)
        text_stats.append({
            "word": word,
            "count": len(texts),
        })
    text_stats.sort(key=lambda x: x["count"], reverse=True)
    return {"video_id": video_id, "word_count": len(unique_words), "words": text_stats}
