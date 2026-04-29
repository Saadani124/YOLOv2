from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database.core import get_db, SearchHistory
from database.service import (
    get_video, get_segments_for_video, segment_to_dict, 
    log_search, get_popular_searches, get_detections_for_video,
    detection_to_dict, update_search_history_for_objects,
    get_visual_texts_for_video, search_global
)
from database.models import SearchRequest, GlobalSearchRequest, GlobalSearchResponse
from services.search import search_transcription
from services.object_detection import search_objects
from core.utils import format_time

router = APIRouter(prefix="/api")

@router.post("/search")
async def search_transcription_endpoint(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    video = get_video(db, request.video_id)
    if not video: raise HTTPException(status_code=404, detail="Video not found.")

    query = request.query.strip()
    if not query:
        db_segments = get_segments_for_video(db, request.video_id)
        results = [
            {
                "id": s.segment_id,
                "start": s.start_time,
                "end": s.end_time,
                "start_formatted": format_time(s.start_time),
                "end_formatted": format_time(s.end_time),
                "text": s.text,
            }
            for s in db_segments
        ]
    else:
        db_segments = get_segments_for_video(db, request.video_id)
        segments = [segment_to_dict(seg, include_words=True) for seg in db_segments]
        results = search_transcription(segments=segments, query=query, full_text=video.full_text)
        log_search(db=db, video_id=request.video_id, query=query, result_count=len(results))
    
    return {
        "query": query,
        "result_count": len(results),
        "results": results,
        "full_text": video.full_text,
    }

@router.post("/search/objects")
async def search_objects_endpoint(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    video = get_video(db, request.video_id)
    if not video: raise HTTPException(status_code=404, detail="Video not found.")

    query = request.query.strip()
    db_detections = get_detections_for_video(db, request.video_id)
    detections = [detection_to_dict(d) for d in db_detections]
    
    detections_for_logic = [
        {
            "timestamp": d["timestamp"],
            "frame_number": d["frame_number"],
            "object_class": d["object_class"],
            "confidence": d["confidence"] / 100.0,
            "bbox": d["bbox"]
        }
        for d in detections
    ]
    
    if not query:
        from services.object_detection import _group_detections
        grouped = _group_detections(detections_for_logic, time_threshold=5.0)
    else:
        grouped = search_objects(detections_for_logic, query)
        update_search_history_for_objects(db=db, video_id=request.video_id, query=query, result_count=len(grouped))

    results = []
    for group in grouped:
        results.append({
            "object_class": group["object_class"],
            "start_time": group["start_time"],
            "end_time": group["end_time"],
            "start_formatted": format_time(group["start_time"]),
            "end_formatted": format_time(group["end_time"]),
            "duration": group["duration"],
            "confidence": round(group["confidence"] * 100, 2),
            "frame_count": group["frame_count"]
        })
    
    return {"query": query, "result_count": len(results), "results": results}

@router.post("/search/visual-text")
async def search_visual_text_endpoint(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    video = get_video(db, request.video_id)
    if not video: raise HTTPException(status_code=404, detail="Video not found.")

    query = request.query.strip()
    db_texts = get_visual_texts_for_video(db, request.video_id, text_query=query if query else None)
    
    results = []
    for t in db_texts:
        results.append({
            "text": t.text,
            "start_time": t.timestamp,
            "end_time": t.timestamp,
            "start_formatted": format_time(t.timestamp),
            "end_formatted": format_time(t.timestamp),
            "duration": 0.0,
            "confidence": round(t.confidence * 100, 2),
            "frame_count": 1
        })
    
    if query:
        search_log = SearchHistory(
            video_id=request.video_id,
            query=query,
            result_count=len(results),
            search_type="ocr",
            clicked_result=False
        )
        db.add(search_log)
        db.commit()
    
    return {"query": query, "result_count": len(results), "results": results}

@router.get("/search-suggestions/{video_id}")
async def get_search_suggestions_endpoint(video_id: str, db: Session = Depends(get_db)):
    suggestions = get_popular_searches(db, video_id, limit=10)
    return {"video_id": video_id, "suggestions": suggestions}


@router.post("/search/global", response_model=GlobalSearchResponse)
async def global_search_endpoint(
    request: GlobalSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search across all videos and group results.
    """
    query = request.query.strip()
    if not query:
        return {"query": "", "total_matches": 0, "video_results": []}
        
    video_results = search_global(db, query)
    
    total_matches = sum(len(v["matches"]) for v in video_results)
    
    return {
        "query": query,
        "total_matches": total_matches,
        "video_results": video_results
    }
