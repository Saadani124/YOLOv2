# VOCO v2 (ScanVD) - System Architecture & Processing Report

This report outlines the data pipeline, AI models, parameter optimization, and backend architecture of **VOCO v2**, a high-performance AI Video Content Scanner. The application ingests video files and extracts deep, searchable metadata—including spoken words, detected objects, and visual text (OCR)—providing users with an advanced sub-second video search interface.

---

## 1. The Data Processing Pipeline

When a user uploads a video, the file follows a strict, asynchronous background processing pipeline to extract and index data without blocking the web server.

### Phase 1: Ingestion & Initialization
1. **Upload:** The video is received via the `/api/upload` endpoint (`routers/video.py`). It is saved to the local `uploads/` directory with a unique UUID.
2. **Metadata & Thumbnail:** The system extracts basic metadata (duration, file size) and uses **FFMPEG** to extract a representative thumbnail at the video's midpoint (`services/ffmpeg.py`).
3. **Task Registration:** The `progress_manager` (`core/progress.py`) registers the video and opens a Server-Sent Events (SSE) stream so the frontend can display real-time progress.

### Phase 2: AI Processing (The Background Worker)
Orchestrated entirely by `tasks/background.py`, the video passes through three sequential AI processing layers:

1. **Audio Transcription:** The audio track is isolated, and the **Whisper** model transcribes the speech, generating exact start and end timestamps for every single word.
2. **Object Detection:** The video frames are sampled (e.g., 1 frame per second). The **YOLO** model scans each frame, identifying objects (e.g., "person", "car", "laptop") and plotting their bounding boxes and confidence scores.
3. **Optical Character Recognition (OCR):** The same sampled frames are passed to **EasyOCR**, which scans for visual text (e.g., words on a poster, street signs, or presentation slides), extracting the text and its screen coordinates.

### Phase 3: Storage & Indexing
1. **Database Commit:** All extracted data is formatted and saved to the relational database (MySQL/SQLite) via `database/service.py`. The database schema (`database/core.py` and `database/models.py`) creates relationships linking the core `Video` to its `Segments`, `Words`, `ObjectDetections`, and `VisualTexts`.
2. **Completion:** The progress stream emits a 100% completion event. The frontend unlocks the video for advanced searching.

### Phase 4: Search & Retrieval
1. **Query Execution:** When the user searches, requests are routed to `routers/search.py`.
2. **Fuzzy Matching:** For transcriptions, the system uses the `RapidFuzz` library to find exact or near-matches, allowing for slight misspellings.
3. **Algorithmic Highlighting:** The frontend (`search.js`) uses an optimized `O(1)` HashMap index to instantly map thousands of search results onto the video timeline without freezing the DOM.

---

## 2. AI Models & Parameter Optimization

To achieve the best possible balance between inference speed and accuracy, we carefully selected and tuned the following models.

### A. Audio Transcription: OpenAI Whisper
* **Role:** Converts spoken audio into text with word-level timestamps.
* **Library:** `whisper`
* **Configuration:** 
  * We use the `base` model (configurable via `.env` `WHISPER_MODEL=base`). It provides exceptional accuracy for general English while remaining fast enough to run locally.
  * **Word Timestamps:** Explicitly enabled (`word_timestamps=True`) to allow the frontend to jump to the *exact second* a word is spoken, rather than just the beginning of a long sentence.
* **Model Comparison (Whisper vs Qwen3-ASR):** Whisper supports ~100 languages with a 6–8% error rate at real-time speeds, making it highly reliable and universal. In contrast, Qwen3-ASR supports ~50 languages but runs up to 10× faster. Qwen3-ASR also performs slightly better on difficult audio (20–25% error rate compared to Whisper's 25–30%). Ultimately, Whisper is chosen for its broader language support, while Qwen3-ASR excels in speed.

### B. Object Detection: YOLOv12n (or YOLOv5n)
* **Role:** Identifies physical objects within the video frames.
* **Library:** `ultralytics`
* **Model Comparison (YOLOv8 vs YOLOv26):** Comparing the small models on a CPU, YOLOv8 achieves 37% accuracy at ~80ms per frame, while YOLOv26 hits 41% accuracy at just ~39ms (twice as fast). This trend continues with the larger models: YOLOv8 reaches ~50% accuracy compared to YOLOv26's ~55%. In short, YOLOv26 provides superior speed and accuracy, making it ideal for systems without a strong GPU.
* **Optimization Parameters (`services/object_detection.py`):**
  ```python
  results = _detection_model(
      frame_rgb,
      conf=0.45,       # Confidence Threshold
      imgsz=640,       # Native resolution processing
      half=True,       # FP16 Half-Precision
      device=device,   # Hardware acceleration
      verbose=False
  )
  ```
* **Why these parameters?**
  * **`conf=0.45`**: Discards weak predictions early. Lowering this (e.g., `0.20`) yields more objects but introduces "noise" (false positives). Raising it (e.g., `0.80`) misses smaller or blurry objects. `0.45` is the optimal sweet spot.
  * **`half=True`**: Forces the model to use 16-bit floats instead of 32-bit floats. This massively accelerates GPU processing and halves VRAM usage with almost zero loss in accuracy.
  * **`imgsz=640`**: Scales the frame down to the exact size the neural network was trained on, preventing the GPU from choking on 4K video frames.

### C. Visual Text Detection: EasyOCR
* **Role:** Reads text from the visual environment (posters, boards, screens).
* **Library:** `easyocr`
* **Optimization Parameters (`services/ocr.py`):**
  * Initialized with `gpu=True` to piggyback off the same hardware acceleration used by YOLO.
  * Filters out text with a confidence score below `0.3` to prevent illegible blurs from polluting the database.
  * Extracts coordinates (`bbox`) to potentially allow future UI features (like drawing boxes around the text).

> **Customization Note:** You can alter how frequently the system scans for objects and text by changing `OBJECT_DETECTION_INTERVAL = 1.0` and `OCR_INTERVAL = 1.0` in `config.py`. A value of `1.0` (1 frame per second) is highly recommended; decreasing it to `0.1` (10 frames per second) will increase metadata accuracy but cause processing times to spike by 10x.

---

## 3. Core Libraries & Infrastructure

* **FastAPI:** The backbone of the backend. Chosen for its extreme speed and native support for asynchronous programming (`async/await`), which is strictly required for handling long-running AI tasks and SSE progress streams simultaneously.
* **SQLAlchemy:** The Object-Relational Mapper (ORM). It abstracts SQL queries into Python code, allowing the app to seamlessly switch between SQLite (for testing) and MySQL (for production) just by changing the `DATABASE_URL`.
* **PyTorch:** The underlying deep-learning tensor framework powering both Whisper and YOLO. It handles memory allocation and CUDA (NVIDIA GPU) parallelization.
* **FFMPEG:** The industry-standard multimedia framework. Used to rip audio tracks out of `.mp4` containers for Whisper, and to extract exact visual frames for YOLO and OCR.

---

## 4. Backend Codebase Architecture

The backend utilizes a modular, enterprise-grade directory structure:

### 📁 `routers/` (API Endpoints)
* **`video.py`**: Handles incoming file uploads, triggers the background worker, serves raw video streams, and handles video deletion.
* **`search.py`**: Handles all POST requests for searching (transcript, objects, visual text).
* **`analysis.py`**: Provides "GET" endpoints to retrieve all compiled data for a video (e.g., returning the full JSON transcript, or unique object tags).
* **`progress.py`**: Houses the Server-Sent Events (SSE) route `/api/progress/{id}`.

### 📁 `services/` (Business & AI Logic)
* **`transcription.py`**: Wrapper for the Whisper model.
* **`object_detection.py`**: Wrapper for the YOLO model. Includes logic for grouping duplicate object detections.
* **`ocr.py`**: Wrapper for the EasyOCR model.
* **`search.py`**: Executes the fuzzy-matching logic using `RapidFuzz` against transcript segments.
* **`ffmpeg.py`**: Interacts with the system's FFMPEG binary to extract thumbnails and validate video codecs.
* **`text_processing.py`**: Uses NLP techniques to extract the most common "keywords" from a video's full text.

### 📁 `database/` (Data Persistence)
* **`core.py`**: Connects to the database using SQLAlchemy engines and defines the ORM Table classes (Video, Segment, Word, ObjectDetection, VisualText).
* **`service.py`**: Contains all CRUD (Create, Read, Update, Delete) functions. Separates SQL logic from the API routers.
* **`models.py`**: Defines Pydantic schemas (e.g., `SearchRequest`). These enforce strict typing on incoming JSON payloads.

### 📁 `tasks/`
* **`background.py`**: The "conductor" of the orchestra. It runs asynchronously, taking the video path and feeding it sequentially to `transcription`, `object_detection`, and `ocr`, before finally saving all outputs via `database.service`.

### 📁 `core/`
* **`progress.py`**: A thread-safe Pub/Sub manager. It allows the `tasks/background.py` worker to broadcast string updates (e.g., "Transcribing...") which are instantly funneled to the frontend via the `routers/progress.py` SSE stream.
* **`utils.py`**: Helper functions for time and size formatting.

### 📄 Root Files
* **`app.py`**: The FastAPI application instance. Sets up CORS, initializes the database, and mounts all the routers.
* **`run.py`**: The Uvicorn server entry point that boots the application.
* **`config.py`**: The central source of truth for all configurable variables (Intervals, Model names, Thresholds, Database URLs).
