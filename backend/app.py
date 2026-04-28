import os
import sys

# --- CRITICAL WINDOWS DLL FIX ---
# This must run before 'torch' or 'torchcodec' are imported to find FFmpeg DLLs
FFMPEG_BIN_PATH = r"C:\ffmpeg\bin"  # Ensure this matches your extraction path
if os.path.exists(FFMPEG_BIN_PATH):
    os.add_dll_directory(FFMPEG_BIN_PATH)
# -------------------------------

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import (
    CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS, FRONTEND_DIR, DATABASE_URL
)
from database.core import init_db
from routers import video, progress, search, analysis
from services.ffmpeg import find_ffmpeg, patch_whisper_audio_loader, is_ffmpeg_available



# Initialize FastAPI app
app = FastAPI(
    title="VOCO v2 - AI Video Content Scanner",
    description="Upload videos and search for specific moments using AI transcription and object detection",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)

# Startup banner
print("\n" + "="*70)
print("  VOCO v2 — AI Video Content Scanner")
print("  Enhanced Search & Object Detection")
print("="*70 + "\n")

# Check for ffmpeg and patch Whisper if needed
print("🔧 Checking dependencies...")
FFMPEG_AVAILABLE = find_ffmpeg()
if FFMPEG_AVAILABLE:
    patch_whisper_audio_loader()
else:
    print("\n⚠️  WARNING: ffmpeg not found. Video upload will fail.")
    print("    Install with: pip install imageio-ffmpeg\n")

# Initialize database
print("\n💾 Setting up database...")
try:
    init_db()
    # Masking password for logs
    db_display = DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'configured'
    print(f"✓ Database connected: {db_display}")
except Exception as e:
    print(f"⚠️  WARNING: Database initialization failed: {e}")
    print("    Check your DATABASE_URL in config.py or .env")


# Include API routes
app.include_router(video.router)
app.include_router(progress.router)
app.include_router(search.router)
app.include_router(analysis.router)

# Serve frontend static files
if os.path.exists(FRONTEND_DIR):
    print(f"\n🌐 Frontend directory found: {FRONTEND_DIR}")
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    print("✓ Serving frontend at http://localhost:8000")
else:
    print(f"\n⚠️  WARNING: Frontend directory not found at {FRONTEND_DIR}")
    print("    Frontend files will not be served")

print("\n" + "="*70)
print("  🚀 Backend initialization complete!")
print("  🌐 Server ready at http://localhost:8000")
print("  📚 API docs at http://localhost:8000/docs")
print("="*70 + "\n")


@app.get("/health")
async def health_check():
    """
    Health check endpoint with feature status.
    """
    db_status = "connected"
    try:
        from database.core import SessionLocal
        db = SessionLocal()
        # Simple query to test connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": {
            "ffmpeg_available": is_ffmpeg_available(),
            "database_status": db_status,
            "frontend_available": os.path.exists(FRONTEND_DIR),
        }
    }


@app.get("/features")
async def list_features():
    """
    List all available features and their configuration.
    """
    from config import (
        WHISPER_MODEL, SEARCH_FUZZY_THRESHOLD, SEARCH_MAX_RESULTS,
        SEARCH_ENABLE_STEMMING
    )
    
    return {
        "transcription": {
            "model": WHISPER_MODEL,
            "word_timestamps": True,
        },
        "search": {
            "fuzzy_threshold": SEARCH_FUZZY_THRESHOLD,
            "max_results": SEARCH_MAX_RESULTS,
            "stemming_enabled": SEARCH_ENABLE_STEMMING,
        },
        "storage": {
            "database": "MySQL" if "mysql" in DATABASE_URL else "Other",
            "persistent": True,
        },
    }