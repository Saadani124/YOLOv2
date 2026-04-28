
from typing import Dict, List, Optional
from pydantic import BaseModel


class WordTimestamp(BaseModel):
    """Individual word with timestamp"""
    word: str
    start: float
    end: float
    start_formatted: str
    end_formatted: str


class TranscriptSegment(BaseModel):
    """Transcript segment with word-level detail"""
    id: int
    start: float
    end: float
    start_formatted: str
    end_formatted: str
    text: str
    words: Optional[List[WordTimestamp]] = None


class VideoTranscription(BaseModel):
    """Complete video transcription data"""
    segments: List[TranscriptSegment]
    full_text: str
    language: str
    video_path: str
    video_filename: str
    original_name: str


class SearchRequest(BaseModel):
    """Search request model"""
    video_id: str
    query: str


class SearchMatch(BaseModel):
    """Individual search result match"""
    segment_id: int
    start: float
    end: float
    start_formatted: str
    end_formatted: str
    text: str
    match_type: str
    precise_start: Optional[float] = None
    precise_start_formatted: Optional[str] = None
    matched_words: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """Search response model"""
    query: str
    result_count: int
    results: List[SearchMatch]
    full_text: str


transcriptions: Dict[str, VideoTranscription] = {}

#tahdhir ll BD
def store_transcription(video_id: str, data: VideoTranscription):
    """Store a transcription"""
    transcriptions[video_id] = data


def get_transcription(video_id: str) -> Optional[VideoTranscription]:
    """Retrieve a transcription"""
    return transcriptions.get(video_id)


def delete_transcription(video_id: str):
    """Delete a transcription"""
    if video_id in transcriptions:
        del transcriptions[video_id]


def transcription_exists(video_id: str) -> bool:
    """Check if a transcription exists"""
    return video_id in transcriptions
