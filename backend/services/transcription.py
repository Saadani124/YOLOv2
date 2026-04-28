
import whisper
from typing import Dict, List, Optional
from config import WHISPER_MODEL, ENABLE_WORD_TIMESTAMPS, WHISPER_FP16, DEVICE, MODELS_DIR
from database.models import TranscriptSegment, WordTimestamp
from core.utils import format_time
from core.progress import progress_manager

# Load Whisper model
print(f"Loading Whisper model '{WHISPER_MODEL}' on device '{DEVICE}'...")
model = whisper.load_model(WHISPER_MODEL, device=DEVICE, download_root=MODELS_DIR)
print(f"Whisper model '{WHISPER_MODEL}' loaded successfully!")


def transcribe_video(video_path: str, task_id: Optional[str] = None) -> Dict:
    """
    Transcribe a video file using Whisper.
    
    Args:
        video_path: Path to the video file
        task_id: Optional task ID for progress reporting
        
    Returns:
        Dictionary containing transcription data with segments and metadata
    """
    if task_id:
        progress_manager.update_progress(task_id, "transcribing", 0, "Starting transcription...")
    
    print(f"Transcribing video: {video_path}")
    
    # Report progress (since Whisper doesn't have hooks, we report stages)
    if task_id:
        progress_manager.update_progress(task_id, "transcribing", 10, "Loading audio and model...")

    result = model.transcribe(
        video_path,
        word_timestamps=ENABLE_WORD_TIMESTAMPS,
        verbose=False,
        fp16=WHISPER_FP16,
    )
    
    if task_id:
        detected_lang = result.get("language", "unknown")
        progress_manager.add_log(task_id, f"Detected language: {detected_lang}")
        progress_manager.update_progress(task_id, "transcribing", 100, "Transcription complete!")
    
    print(f"Transcription complete!")
    return result


def process_transcription_segments(whisper_result: Dict) -> List[TranscriptSegment]:
    """
    Process Whisper transcription result into structured segments.
    
    Args:
        whisper_result: Raw result from Whisper transcription
        
    Returns:
        List of TranscriptSegment objects with word-level timestamps
    """
    segments = []
    
    for segment in whisper_result.get("segments", []):
        seg_data = {
            "id": segment["id"],
            "start": segment["start"],
            "end": segment["end"],
            "start_formatted": format_time(segment["start"]),
            "end_formatted": format_time(segment["end"]),
            "text": segment["text"].strip(),
        }

        # Include word-level timestamps if available
        if "words" in segment and segment["words"]:
            seg_data["words"] = [
                WordTimestamp(
                    word=w["word"].strip(),
                    start=w["start"],
                    end=w["end"],
                    start_formatted=format_time(w["start"]),
                    end_formatted=format_time(w["end"]),
                )
                for w in segment["words"]
            ]

        segments.append(TranscriptSegment(**seg_data))
    
    return segments


def get_full_text(whisper_result: Dict) -> str:
    """
    Extract full text from Whisper result.
    
    Args:
        whisper_result: Raw result from Whisper transcription
        
    Returns:
        Complete transcription text
    """
    return whisper_result.get("text", "").strip()


def get_language(whisper_result: Dict) -> str:
    """
    Extract detected language from Whisper result.
    
    Args:
        whisper_result: Raw result from Whisper transcription
        
    Returns:
        Language code (e.g., 'en', 'fr', 'es')
    """
    return whisper_result.get("language", "unknown")
