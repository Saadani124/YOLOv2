from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from core.progress import progress_manager

router = APIRouter(prefix="/api")

@router.get("/progress/{video_id}")
async def get_progress_stream(video_id: str):
    """
    SSE endpoint for real-time progress updates.
    """
    return StreamingResponse(
        progress_manager.subscribe(video_id),
        media_type="text/event-stream"
    )
