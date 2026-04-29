import os
import traceback
import asyncio
from config import ENABLE_OBJECT_DETECTION, ENABLE_OCR, UPLOAD_DIR
from core.progress import progress_manager
from database.core import get_db_session
from database.service import (
    create_video, get_video, create_segment, create_word,
    create_object_detection, create_visual_text
)
from services.transcription import (
    transcribe_video, process_transcription_segments,
    get_full_text, get_language
)
from services.object_detection import detect_objects_in_video
from services.ocr import detect_text_in_video
from services.ffmpeg import extract_thumbnail

async def process_video_background(
    video_id: str,
    video_path: str,
    video_filename: str,
    original_name: str,
    file_size: int
):
    """
    Background worker to handle transcription, object detection, and OCR.
    """
    db = get_db_session()
    try:
        # 1. Transcribe
        progress_manager.update_progress(video_id, "transcribing", 0, "Initializing transcription...")
        whisper_result = await asyncio.to_thread(transcribe_video, video_path, video_id)
        
        segments = process_transcription_segments(whisper_result)
        full_text = get_full_text(whisper_result)
        language = get_language(whisper_result)
        
        # Calculate duration using cv2 for better accuracy (and fallback if no audio)
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        duration = (total_frames / fps) if fps > 0 else (segments[-1].end if segments else 0.0)
        
        # 2. Initial Database Record
        progress_manager.update_progress(video_id, "indexing", 0, "Saving video metadata...")
        db_video = create_video(
            db=db,
            video_id=video_id,
            filename=video_filename,
            original_name=original_name,
            file_path=video_path,
            file_size=file_size,
            duration=duration,
            language=language,
            full_text=full_text
        )

        # 2.5 Extract Thumbnail
        progress_manager.update_progress(video_id, "indexing", 0, "Extracting thumbnail...")
        thumbnail_path = os.path.join(UPLOAD_DIR, f"{video_id}.jpg")
        thumb_time = duration / 2.0 if duration > 2.0 else 1.0
        await asyncio.to_thread(extract_thumbnail, video_path, thumbnail_path, thumb_time)

        # 3. Object Detection
        if ENABLE_OBJECT_DETECTION:
            progress_manager.update_progress(video_id, "detecting", 0, "Starting object detection...")
            detections = await asyncio.to_thread(detect_objects_in_video, video_path, None, video_id)
            if detections:
                for detection in detections:
                    create_object_detection(
                        db=db,
                        video_id=video_id,
                        frame_number=detection["frame_number"],
                        timestamp=detection["timestamp"],
                        object_class=detection["object_class"],
                        confidence=detection["confidence"],
                        bbox_x=detection["bbox"]["x"],
                        bbox_y=detection["bbox"]["y"],
                        bbox_width=detection["bbox"]["width"],
                        bbox_height=detection["bbox"]["height"]
                    )
                
        # 3.5 OCR
        if ENABLE_OCR:
            progress_manager.update_progress(video_id, "indexing", 0, "Scanning for visual text...")
            visual_texts = await asyncio.to_thread(detect_text_in_video, video_path, None, video_id)
            if visual_texts:
                for text_item in visual_texts:
                    create_visual_text(
                        db=db,
                        video_id=video_id,
                        frame_number=text_item["frame_number"],
                        timestamp=text_item["timestamp"],
                        text=text_item["text"],
                        confidence=text_item["confidence"],
                        bbox_x=text_item["bbox"]["x"],
                        bbox_y=text_item["bbox"]["y"],
                        bbox_width=text_item["bbox"]["width"],
                        bbox_height=text_item["bbox"]["height"]
                    )
        
        # 4. Save Segments and Words
        progress_manager.update_progress(video_id, "indexing", 50, "Saving transcription segments...")
        for i, seg in enumerate(segments):
            db_segment = create_segment(
                db=db,
                video_id=video_id,
                segment_id=seg.id,
                start_time=seg.start,
                end_time=seg.end,
                text=seg.text
            )
            if seg.words:
                for w in seg.words:
                    create_word(
                        db=db,
                        segment_id=db_segment.id,
                        word=w.word,
                        start_time=w.start,
                        end_time=w.end
                    )
        
        progress_manager.complete_task(video_id, "Video processed and indexed successfully!")
        print(f"Background processing complete for {video_id}")

    except Exception as e:
        print(f"Error in background processing for {video_id}: {str(e)}")
        traceback.print_exc()
        progress_manager.set_error(video_id, str(e))
        if os.path.exists(video_path):
            try:
                if not get_video(db, video_id):
                    os.remove(video_path)
            except:
                pass
    finally:
        db.close()
