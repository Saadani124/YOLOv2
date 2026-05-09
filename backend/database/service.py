
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from datetime import datetime

from database.core import Video, Segment, Word, SearchHistory, ObjectDetection, VisualText
from core.utils import format_time


def create_video(
    db: Session,
    video_id: str,
    filename: str,
    original_name: str,
    file_path: str,
    file_size: int,
    duration: float,
    language: str,
    full_text: str
) -> Video:
    """
    Create a new video record in the database.
    
    Args:
        db: Database session
        video_id: Unique UUID identifier for the video
        filename: Name of the file stored on disk
        original_name: Original name of the uploaded file
        file_path: Absolute path to the video file
        file_size: Size of the file in bytes
        duration: Video duration in seconds
        language: Detected language code (e.g., 'en')
        full_text: Complete transcription text
        
    Returns:
        The created Video object
    """
    video = Video(
        video_id=video_id,
        filename=filename,
        original_name=original_name,
        file_path=file_path,
        file_size=file_size,
        duration=duration,
        language=language,
        full_text=full_text,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def get_video(db: Session, video_id: str) -> Optional[Video]:
    """Retrieve a video by its unique UUID."""
    return db.query(Video).filter(Video.video_id == video_id).first()


def get_all_videos(db: Session, skip: int = 0, limit: int = 100) -> List[Video]:
    """List all videos with pagination."""
    return db.query(Video).offset(skip).limit(limit).all()


def delete_video(db: Session, video_id: str) -> bool:
    """Delete a video record from the database."""
    video = get_video(db, video_id)
    if video:
        db.delete(video)
        db.commit()
        return True
    return False


def create_segment(
    db: Session,
    video_id: str,
    segment_id: int,
    start_time: float,
    end_time: float,
    text: str,
    speaker_db_id: Optional[int] = None,
    confidence: Optional[float] = None,
    commit: bool = True
) -> Segment:
    """
    Create a transcription segment record.
    
    Args:
        db: Database session
        video_id: Associated video UUID
        segment_id: Whisper-provided segment index
        start_time: Start time in seconds
        end_time: End time in seconds
        text: Segment text content
        speaker_db_id: ID of the speaker (if diarization is used)
        confidence: Recognition confidence (0.0-1.0)
        commit: If False, defers db.commit() for batch processing efficiency
        
    Returns:
        The created Segment object
    """
    segment = Segment(
        video_id=video_id,
        segment_id=segment_id,
        start_time=start_time,
        end_time=end_time,
        text=text,
        confidence=confidence
    )
    db.add(segment)
    if commit:
        db.commit()
        db.refresh(segment)
    return segment


def get_segments_for_video(db: Session, video_id: str) -> List[Segment]:
    """Get all transcription segments for a specific video, ordered by time."""
    return db.query(Segment).filter(
        Segment.video_id == video_id
    ).order_by(Segment.start_time).all()


def create_word(
    db: Session,
    segment_id: int,
    word: str,
    start_time: float,
    end_time: float,
    confidence: Optional[float] = None,
    commit: bool = True
) -> Word:
    """
    Create a word-level timestamp record.
    
    Args:
        db: Database session
        segment_id: Parent segment internal ID (not UUID)
        word: Individual word text
        start_time: Start time in seconds
        end_time: End time in seconds
        confidence: Word-level confidence score
        commit: If False, defers db.commit() for batch processing efficiency
        
    Returns:
        The created Word object
    """
    word_obj = Word(
        segment_id=segment_id,
        word=word,
        start_time=start_time,
        end_time=end_time,
        confidence=confidence,
    )
    db.add(word_obj)
    if commit:
        db.commit()
        db.refresh(word_obj)
    return word_obj


def search_segments(
    db: Session,
    video_id: str,
    query: str
) -> List[Segment]:
    """Search for segments containing specific text in a specific video."""
    return db.query(Segment).filter(
        Segment.video_id == video_id,
        Segment.text.like(f"%{query}%")
    ).all()


def log_search(
    db: Session,
    video_id: str,
    query: str,
    result_count: int,
    clicked_result: bool = False
):
    """Log search queries for analytics and popular search tracking."""
    search_log = SearchHistory(
        video_id=video_id,
        query=query,
        result_count=result_count,
        clicked_result=clicked_result,
    )
    db.add(search_log)
    db.commit()


def get_popular_searches(db: Session, video_id: str, limit: int = 10) -> List[str]:
    """Retrieve the most frequent search queries for a video."""
    from sqlalchemy import func
    
    results = db.query(
        SearchHistory.query,
        func.count(SearchHistory.query).label('count')
    ).filter(
        SearchHistory.video_id == video_id
    ).group_by(
        SearchHistory.query
    ).order_by(
        func.count(SearchHistory.query).desc()
    ).limit(limit).all()
    
    return [r[0] for r in results]


def segment_to_dict(segment: Segment, include_words: bool = False) -> Dict:
    """Serialize a Segment object to a dictionary for API responses."""
    result = {
        "id": segment.segment_id,
        "start": segment.start_time,
        "end": segment.end_time,
        "start_formatted": format_time(segment.start_time),
        "end_formatted": format_time(segment.end_time),
        "text": segment.text,
    }
    
    if include_words and segment.words:
        result["words"] = [
            {
                "word": w.word,
                "start": w.start_time,
                "end": w.end_time,
                "start_formatted": format_time(w.start_time),
                "end_formatted": format_time(w.end_time),
            }
            for w in segment.words
        ]
    
    return result


def create_object_detection(
    db: Session,
    video_id: str,
    frame_number: int,
    timestamp: float,
    object_class: str,
    confidence: float,
    bbox_x: float = None,
    bbox_y: float = None,
    bbox_width: float = None,
    bbox_height: float = None,
    commit: bool = True
) -> ObjectDetection:
    """
    Create an object detection record.
    
    Args:
        db: Database session
        video_id: Associated video UUID
        frame_number: Sequential frame index where object was found
        timestamp: Time in seconds
        object_class: Label (e.g., 'person', 'dog')
        confidence: YOLO confidence score (0.0-1.0)
        bbox_x: Bounding box left coordinate
        bbox_y: Bounding box top coordinate
        bbox_width: Bounding box width
        bbox_height: Bounding box height
        commit: If False, defers db.commit() for batch processing efficiency
        
    Returns:
        The created ObjectDetection object
    """
    detection = ObjectDetection(
        video_id=video_id,
        frame_number=frame_number,
        timestamp=timestamp,
        object_class=object_class,
        confidence=confidence,
        bbox_x=bbox_x,
        bbox_y=bbox_y,
        bbox_width=bbox_width,
        bbox_height=bbox_height
    )
    db.add(detection)
    if commit:
        db.commit()
        db.refresh(detection)
    return detection


def get_detections_for_video(
    db: Session,
    video_id: str,
    object_class: Optional[str] = None,
    min_confidence: float = 0.5
) -> List[ObjectDetection]:
    """Retrieve object detections for a video, filtered by class or confidence."""
    query = db.query(ObjectDetection).filter(
        ObjectDetection.video_id == video_id,
        ObjectDetection.confidence >= min_confidence
    )
    
    if object_class:
        query = query.filter(ObjectDetection.object_class.like(f"%{object_class}%"))
    
    return query.order_by(ObjectDetection.timestamp).all()


def get_unique_objects_in_video(db: Session, video_id: str) -> List[str]:
    """Get a list of all unique object classes found in a video."""
    from sqlalchemy import distinct
    
    results = db.query(distinct(ObjectDetection.object_class)).filter(
        ObjectDetection.video_id == video_id
    ).all()
    
    return [r[0] for r in results]


def detection_to_dict(detection: ObjectDetection) -> Dict:
    """Serialize an ObjectDetection object to a dictionary."""
    return {
        "id": detection.id,
        "frame_number": detection.frame_number,
        "timestamp": detection.timestamp,
        "timestamp_formatted": format_time(detection.timestamp),
        "object_class": detection.object_class,
        "confidence": round(detection.confidence * 100, 2),
        "bbox": {
            "x": detection.bbox_x,
            "y": detection.bbox_y,
            "width": detection.bbox_width,
            "height": detection.bbox_height
        } if detection.bbox_x is not None else None
    }


def update_search_history_for_objects(
    db: Session,
    video_id: str,
    query: str,
    result_count: int
):
    """Log an object-based search query."""
    search_log = SearchHistory(
        video_id=video_id,
        query=query,
        result_count=result_count,
        search_type="object",
        clicked_result=False
    )
    db.add(search_log)
    db.commit()


def create_visual_text(
    db: Session,
    video_id: str,
    frame_number: int,
    timestamp: float,
    text: str,
    confidence: float,
    bbox_x: float = None,
    bbox_y: float = None,
    bbox_width: float = None,
    bbox_height: float = None,
    commit: bool = True
) -> VisualText:
    """
    Create a visual text (OCR) record.
    
    Args:
        db: Database session
        video_id: Associated video UUID
        frame_number: Frame index
        timestamp: Time in seconds
        text: Detected text content
        confidence: OCR confidence score (0.0-1.0)
        commit: If False, defers db.commit() for batch processing efficiency
    """
    vt = VisualText(
        video_id=video_id,
        frame_number=frame_number,
        timestamp=timestamp,
        text=text,
        confidence=confidence,
        bbox_x=bbox_x,
        bbox_y=bbox_y,
        bbox_width=bbox_width,
        bbox_height=bbox_height
    )
    db.add(vt)
    if commit:
        db.commit()
        db.refresh(vt)
    return vt


def get_visual_texts_for_video(
    db: Session,
    video_id: str,
    text_query: Optional[str] = None,
    min_confidence: float = 0.5
) -> List[VisualText]:
    """Retrieve OCR results for a video, filtered by content."""
    query = db.query(VisualText).filter(
        VisualText.video_id == video_id,
        VisualText.confidence >= min_confidence
    )
    
    if text_query:
        query = query.filter(VisualText.text.like(f"%{text_query}%"))
    
    return query.order_by(VisualText.timestamp).all()


def get_unique_words_in_video(db: Session, video_id: str) -> List[str]:
    """Get list of unique visual text strings detected in a video."""
    from sqlalchemy import distinct
    results = db.query(distinct(VisualText.text)).filter(
        VisualText.video_id == video_id
    ).all()
    return [r[0] for r in results]


def visual_text_to_dict(vt: VisualText) -> Dict:
    """Serialize a VisualText object to a dictionary."""
    return {
        "id": vt.id,
        "frame_number": vt.frame_number,
        "timestamp": vt.timestamp,
        "timestamp_formatted": format_time(vt.timestamp),
        "text": vt.text,
        "confidence": round(vt.confidence * 100, 2),
        "bbox": {
            "x": vt.bbox_x,
            "y": vt.bbox_y,
            "width": vt.bbox_width,
            "height": vt.bbox_height
        } if vt.bbox_x is not None else None
    }


def search_global(db: Session, query: str) -> List[Dict]:
    """
    Perform a unified search across all videos, checking transcripts, 
    detected objects, and visual text (OCR).
    
    Args:
        db: Database session
        query: User search string
        
    Returns:
        List of results grouped by video
    """
    query_clean = query.strip().lower()
    if not query_clean:
        return []
        
    results_by_video = {}
    
    # 1. Search Transcripts
    segments = db.query(Segment, Video).join(Video, Segment.video_id == Video.video_id).filter(
        Segment.text.like(f"%{query_clean}%")
    ).all()
    
    for seg, vid in segments:
        if vid.video_id not in results_by_video:
            results_by_video[vid.video_id] = {
                "video_id": vid.video_id,
                "video_name": vid.original_name,
                "duration": vid.duration,
                "language": vid.language,
                "matches": []
            }
        
        results_by_video[vid.video_id]["matches"].append({
            "timestamp": seg.start_time,
            "timestamp_formatted": format_time(seg.start_time),
            "text": seg.text,
            "match_type": "transcript",
            "score": 100.0
        })
        
    # 2. Search Objects
    objects = db.query(ObjectDetection, Video).join(Video, ObjectDetection.video_id == Video.video_id).filter(
        ObjectDetection.object_class.like(f"%{query_clean}%")
    ).all()
    
    for obj, vid in objects:
        if vid.video_id not in results_by_video:
            results_by_video[vid.video_id] = {
                "video_id": vid.video_id,
                "video_name": vid.original_name,
                "duration": vid.duration,
                "language": vid.language,
                "matches": []
            }
            
        results_by_video[vid.video_id]["matches"].append({
            "timestamp": obj.timestamp,
            "timestamp_formatted": format_time(obj.timestamp),
            "text": f"Detected object: {obj.object_class}",
            "match_type": "object",
            "score": obj.confidence * 100.0
        })
        
    # 3. Search Visual Text (OCR)
    vtexts = db.query(VisualText, Video).join(Video, VisualText.video_id == Video.video_id).filter(
        VisualText.text.like(f"%{query_clean}%")
    ).all()
    
    for vt, vid in vtexts:
        if vid.video_id not in results_by_video:
            results_by_video[vid.video_id] = {
                "video_id": vid.video_id,
                "video_name": vid.original_name,
                "duration": vid.duration,
                "language": vid.language,
                "matches": []
            }
            
        results_by_video[vid.video_id]["matches"].append({
            "timestamp": vt.timestamp,
            "timestamp_formatted": format_time(vt.timestamp),
            "text": f"Visual text: {vt.text}",
            "match_type": "ocr",
            "score": vt.confidence * 100.0
        })
        
    # Sort matches within each video by timestamp
    for vid_id in results_by_video:
        results_by_video[vid_id]["matches"].sort(key=lambda x: x["timestamp"])
        
    return list(results_by_video.values())

def get_collection_stats(db: Session) -> Dict:
    """Aggregate statistics for the entire video collection (languages, objects, text)."""
    from sqlalchemy import func, distinct
    
    # Language distribution
    languages = db.query(Video.language, func.count(Video.id)).group_by(Video.language).all()
    lang_stats = [{"value": l[0], "count": l[1]} for l in languages if l[0]]
    
    # Top detected objects
    objects = db.query(ObjectDetection.object_class, func.count(distinct(ObjectDetection.video_id))).group_by(ObjectDetection.object_class).order_by(func.count(distinct(ObjectDetection.video_id)).desc()).limit(15).all()
    obj_stats = [{"value": o[0], "count": o[1]} for o in objects]
    
    # Top visual text occurrences
    ocr = db.query(VisualText.text, func.count(distinct(VisualText.video_id))).group_by(VisualText.text).order_by(func.count(distinct(VisualText.video_id)).desc()).limit(15).all()
    ocr_stats = [{"value": t[0], "count": t[1]} for t in ocr]
    
    return {
        "languages": lang_stats,
        "objects": obj_stats,
        "visual_text": ocr_stats
    }

def get_videos_by_collection(db: Session, category: str, value: str) -> List[Video]:
    """Filter videos based on collection statistics (e.g., all videos with 'person' detected)."""
    if category == "language":
        return db.query(Video).filter(Video.language == value).all()
    elif category == "object":
        return db.query(Video).join(ObjectDetection).filter(ObjectDetection.object_class == value).distinct().all()
    elif category == "ocr":
        return db.query(Video).join(VisualText).filter(VisualText.text == value).distinct().all()
    return []
