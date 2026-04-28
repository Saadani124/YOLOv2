
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

    return db.query(Video).filter(Video.video_id == video_id).first()


def get_all_videos(db: Session, skip: int = 0, limit: int = 100) -> List[Video]:

    return db.query(Video).offset(skip).limit(limit).all()


def delete_video(db: Session, video_id: str) -> bool:

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
    confidence: Optional[float] = None
) -> Segment:

    segment = Segment(
        video_id=video_id,
        segment_id=segment_id,
        start_time=start_time,
        end_time=end_time,
        text=text,
        confidence=confidence
    )
    db.add(segment)
    db.commit()
    db.refresh(segment)
    return segment


def get_segments_for_video(db: Session, video_id: str) -> List[Segment]:
    """
    Get all segments for a video.
    
    Args:
        db: Database session
        video_id: Video identifier
        
    Returns:
        List of Segment objects ordered by start time
    """
    return db.query(Segment).filter(
        Segment.video_id == video_id
    ).order_by(Segment.start_time).all()


def create_word(
    db: Session,
    segment_id: int,
    word: str,
    start_time: float,
    end_time: float,
    confidence: Optional[float] = None
) -> Word:
    """
    Create a word timestamp record.
    
    Args:
        db: Database session
        segment_id: Parent segment database ID
        word: The word text
        start_time: Start time in seconds
        end_time: End time in seconds
        confidence: Recognition confidence
        
    Returns:
        Created Word object
    """
    word_obj = Word(
        segment_id=segment_id,
        word=word,
        start_time=start_time,
        end_time=end_time,
        confidence=confidence,
    )
    db.add(word_obj)
    db.commit()
    db.refresh(word_obj)
    return word_obj


def search_segments(
    db: Session,
    video_id: str,
    query: str
) -> List[Segment]:
    """
    Search segments by text content.
    
    Args:
        db: Database session
        video_id: Video to search in
        query: Search query
        
    Returns:
        List of matching Segment objects
    """
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
    """
    Log a search query for analytics.
    
    Args:
        db: Database session
        video_id: Video being searched
        query: Search query
        result_count: Number of results found
        clicked_result: Whether user clicked a result
    """
    search_log = SearchHistory(
        video_id=video_id,
        query=query,
        result_count=result_count,
        clicked_result=clicked_result,
    )
    db.add(search_log)
    db.commit()


def get_popular_searches(db: Session, video_id: str, limit: int = 10) -> List[str]:
    """
    Get most popular searches for a video.
    
    Args:
        db: Database session
        video_id: Video identifier
        limit: Maximum number of queries to return
        
    Returns:
        List of popular search queries
    """
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
    """
    Convert Segment object to dictionary.
    
    Args:
        segment: Segment database object
        include_words: Whether to include word-level data
        
    Returns:
        Dictionary representation
    """
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
    bbox_height: float = None
) -> ObjectDetection:
    """
    Create an object detection record.
    
    Args:
        db: Database session
        video_id: Associated video ID
        frame_number: Frame number in video
        timestamp: Time in seconds
        object_class: Detected object class (e.g., "car", "person")
        confidence: Detection confidence (0.0-1.0)
        bbox_x: Bounding box X coordinate (optional)
        bbox_y: Bounding box Y coordinate (optional)
        bbox_width: Bounding box width (optional)
        bbox_height: Bounding box height (optional)
        
    Returns:
        Created ObjectDetection object
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
    db.commit()
    db.refresh(detection)
    return detection


def get_detections_for_video(
    db: Session,
    video_id: str,
    object_class: Optional[str] = None,
    min_confidence: float = 0.5
) -> List[ObjectDetection]:
    """
    Get object detections for a video, optionally filtered by class.
    
    Args:
        db: Database session
        video_id: Video identifier
        object_class: Filter by object class (optional)
        min_confidence: Minimum confidence threshold
        
    Returns:
        List of ObjectDetection objects
    """
    query = db.query(ObjectDetection).filter(
        ObjectDetection.video_id == video_id,
        ObjectDetection.confidence >= min_confidence
    )
    
    if object_class:
        query = query.filter(ObjectDetection.object_class.like(f"%{object_class}%"))
    
    return query.order_by(ObjectDetection.timestamp).all()


def get_unique_objects_in_video(db: Session, video_id: str) -> List[str]:
    """
    Get list of unique object classes detected in a video.
    
    Args:
        db: Database session
        video_id: Video identifier
        
    Returns:
        List of unique object class names
    """
    from sqlalchemy import distinct
    
    results = db.query(distinct(ObjectDetection.object_class)).filter(
        ObjectDetection.video_id == video_id
    ).all()
    
    return [r[0] for r in results]


def detection_to_dict(detection: ObjectDetection) -> Dict:
    """
    Convert ObjectDetection object to dictionary.
    
    Args:
        detection: ObjectDetection database object
        
    Returns:
        Dictionary representation
    """
    return {
        "id": detection.id,
        "frame_number": detection.frame_number,
        "timestamp": detection.timestamp,
        "timestamp_formatted": format_time(detection.timestamp),
        "object_class": detection.object_class,
        "confidence": round(detection.confidence * 100, 2),  # Convert to percentage
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
    """
    Log an object search query.
    
    Args:
        db: Database session
        video_id: Video being searched
        query: Search query (object class)
        result_count: Number of results found
    """
    from database.core import SearchHistory
    
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
    bbox_height: float = None
) -> VisualText:
    """Create a visual text (OCR) record."""
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
    db.commit()
    db.refresh(vt)
    return vt


def get_visual_texts_for_video(
    db: Session,
    video_id: str,
    text_query: Optional[str] = None,
    min_confidence: float = 0.5
) -> List[VisualText]:
    """Get OCR texts for a video, optionally filtered by text."""
    query = db.query(VisualText).filter(
        VisualText.video_id == video_id,
        VisualText.confidence >= min_confidence
    )
    
    if text_query:
        query = query.filter(VisualText.text.like(f"%{text_query}%"))
    
    return query.order_by(VisualText.timestamp).all()


def get_unique_words_in_video(db: Session, video_id: str) -> List[str]:
    """Get list of unique OCR words detected in a video."""
    from sqlalchemy import distinct
    results = db.query(distinct(VisualText.text)).filter(
        VisualText.video_id == video_id
    ).all()
    return [r[0] for r in results]


def visual_text_to_dict(vt: VisualText) -> Dict:
    """Convert VisualText object to dictionary."""
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