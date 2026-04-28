"""
Configuration settings for ScanVD
Contains all app constants and environment configuration
"""
import os
import torch
from dotenv import load_dotenv

load_dotenv()

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
MODELS_DIR = os.path.join(BASE_DIR, "models")
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# Hugging Face Configuration
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
if HUGGINGFACE_TOKEN:
    print(f"HF token loaded (Ends with: ...{HUGGINGFACE_TOKEN[-4:]})")
else:
    print("Warning: HUGGINGFACE_TOKEN not found in .env")

# Set Model Cache Paths (prevents re-downloading)
os.environ["HF_HOME"] = MODELS_DIR
os.environ["HF_HUB_CACHE"] = MODELS_DIR
os.environ["TORCH_HOME"] = MODELS_DIR
os.environ["TRANSFORMERS_CACHE"] = MODELS_DIR

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:@localhost:3306/scanvd"
)

# File upload settings
MAX_FILE_SIZE_MB = 500
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}

# Whisper model settings
WHISPER_MODEL = "base"  # Options: tiny, base, small, medium, large
ENABLE_WORD_TIMESTAMPS = True
WHISPER_FP16 = True  # Enable for significant speed boost on NVIDIA GPU

# Device Selection (Prioritize NVIDIA GPU)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"--- DEVICE SELECTED: {DEVICE.upper()} ---")


# Object Detection settings
ENABLE_OBJECT_DETECTION = True  # Enable/disable object detection
OBJECT_DETECTION_INTERVAL = 1.0  # Optional interval setting

# OCR (Optical Character Recognition) settings
ENABLE_OCR = True  # Enable/disable text detection in video frames
OCR_INTERVAL = 1.0  # Extract frame every N seconds for OCR

# Determine YOLO model path (YOLOv12n turbo - attention-centric, faster & more accurate than YOLOv8)
yolo_filename = "yolov12n.pt"
yolo_in_models = os.path.join(MODELS_DIR, yolo_filename)
yolo_in_backend = os.path.join(BASE_DIR, yolo_filename)

if os.path.exists(yolo_in_models):
    OBJECT_DETECTION_MODEL = yolo_in_models
elif os.path.exists(yolo_in_backend):
    OBJECT_DETECTION_MODEL = yolo_in_backend
else:
    OBJECT_DETECTION_MODEL = yolo_filename # Will download if not found

OBJECT_DETECTION_INTERVAL = 1.0  # Process every N seconds of video
OBJECT_DETECTION_CONFIDENCE = 0.5  # Minimum confidence threshold (0.0-1.0)

# Search settings
SEARCH_FUZZY_THRESHOLD = 0.6  # Fuzzy match threshold (0.0 to 1.0)
SEARCH_MAX_RESULTS = 50  # Maximum search results to return
SEARCH_ENABLE_STEMMING = True  # Enable word stemming for better matching
SEARCH_ENABLE_SYNONYMS = False  # Enable synonym matching (experimental)

# CORS settings
CORS_ORIGINS = ["*"]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]

# Server settings
HOST = "0.0.0.0"
PORT = 8000
RELOAD = True


# Performance settings
ENABLE_CACHE = True  # Cache transcription results
CACHE_TTL = 3600  # Cache time-to-live in seconds