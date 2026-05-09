# 🎥 VOCO v2 (ScanVD) — AI-Powered Video Content Scanner

Developed by **Med Adem Hattay** & **Talel Saadani**

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?style=for-the-badge&logo=PyTorch&logoColor=white)](https://pytorch.org/)
[![MySQL](https://img.shields.io/badge/mysql-%2300f.svg?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)

**VOCO v2 (ScanVD)** is an enterprise-grade, asynchronous AI video analysis pipeline. It transforms video files into deep, searchable metadata—combining spoken words, physical objects, and visual text (OCR) into a unified, sub-second search experience.

---

## 🚀 Key Features

*   **🎙️ Smart Transcription:** Powered by **OpenAI Whisper**, providing word-level timestamps for precise seeking.
*   **👁️ Object Detection:** Utilizes **YOLO** (v12n/v5n) to identify objects like people, cars, electronics, and more across video frames.
*   **📝 Visual OCR:** Extracts text from the video environment (slides, signs, posters) using **EasyOCR**.
*   **⚡ Real-time Progress:** Live updates via **Server-Sent Events (SSE)** as the video is processed.
*   **🔍 Advanced Search:** Fuzzy-matching search logic using **RapidFuzz** for high-speed, error-tolerant queries.
*   **📊 Interactive Timeline:** A sleek frontend dashboard with an optimized $O(1)$ HashMap index for instant search result mapping.

---

## 🛠️ Technology Stack

### Backend
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous, High-Performance)
- **Database:** [SQLAlchemy](https://www.sqlalchemy.org/) ORM (supports SQLite/MySQL)
- **Search Logic:** [RapidFuzz](https://github.com/maxbachmann/RapidFuzz)
- **Media Handling:** [FFMPEG](https://ffmpeg.org/) (via `ffmpeg-python`)

### AI Models
- **Transcription:** [OpenAI Whisper](https://github.com/openai/whisper) (Base model for speed & accuracy)
- **Vision:** [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) (High-speed object detection)
- **OCR:** [EasyOCR](https://github.com/JaidedAI/EasyOCR) (Multi-language text detection)

### Frontend
- **Logic:** Vanilla JavaScript (optimized for high-frequency DOM updates)
- **Styling:** Modern CSS3 with a focus on dark mode and premium aesthetics.

---

## 🏆 Why VOCO v2?

Compared to cloud-based alternatives (Google Vision, AWS Rekognition), VOCO v2 offers:

*   **⚡ Performance:** Zero network latency; local execution on your own hardware.
*   **🔒 Privacy:** Your videos never leave your infrastructure. 100% offline processing.
*   **💰 Cost-Effective:** No per-request billing. Leverages open-source models (Whisper, YOLO, EasyOCR).
*   **🔧 Full Control:** Tune every parameter—from OCR scan rates to fuzzy match thresholds.

---

## 🏗️ System Architecture & Pipeline

The project follows a modular, enterprise-grade architecture designed for scalability:

1.  **Ingestion:** Videos are uploaded via a REST API and queued for processing.
2.  **Background Worker:** An asynchronous task runner orchestrates the AI models sequentially.
3.  **Data Persistence:** Extracted metadata (words, objects, text) is stored in a relational database.
4.  **Retrieval:** The search API provides sub-second query results with temporal context (timestamps).

```text
INDEXV2/
├── backend/            # FastAPI Server
│   ├── core/           # SSE Progress & Thread-safe Pub/Sub
│   ├── database/       # SQLAlchemy Models & Service Layer
│   ├── routers/        # API Routing (Video, Search, Analysis, Progress)
│   ├── services/       # AI Logic (Whisper, YOLO, OCR, RapidFuzz)
│   ├── tasks/          # Background orchestration
│   ├── app.py          # FastAPI instance
│   ├── config.py       # Central configuration
│   └── run.py          # Entry point
├── frontend/           # Search Dashboard (JS/CSS/HTML)
├── presentation/       # Project presentation assets
├── requirements.txt    # Python dependencies
└── scanvd.sql          # Database schema
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.9+
- [FFMPEG](https://ffmpeg.org/download.html) (Essential for frame and audio extraction)
- [MySQL](https://www.mysql.com/) (Optional: SQLite is supported by default)

### 1. Clone & Environment
```bash
git clone https://github.com/Saadani124/YOLOv2.git
cd YOLOv2
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Variables (.env)
Create a `.env` file in the root directory (optional but recommended):
```env
DATABASE_URL=mysql+pymysql://root:@localhost:3306/scanvd
HUGGINGFACE_TOKEN=your_token_here
WHISPER_MODEL=base
```

### 3. Database
Import the SQL schema if using MySQL:
```bash
mysql -u your_user -p your_db < scanvd.sql
```

### 4. Run
```bash
python backend/run.py
```

---

## 📝 Configuration Details

The system is highly configurable via `backend/config.py`:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `WHISPER_MODEL` | `base` | Model size (`tiny`, `base`, `small`, `medium`, `large`). |
| `OBJECT_DETECTION_MODEL` | `yolov8n.pt` | Fallback model for object detection. |
| `OBJECT_DETECTION_INTERVAL` | `1.0`s | Frequency of object detection scans. |
| `OCR_INTERVAL` | `1.0`s | Frequency of OCR text extraction. |
| `SEARCH_FUZZY_THRESHOLD` | `0.6` | Accuracy threshold for RapidFuzz matching. |
| `DEVICE` | `auto` | Automatically detects `cuda` if available, else `cpu`. |

---

## 🧠 AI Models Deep Dive

### **OpenAI Whisper**
- **Mode:** `word_timestamps=True`
- **Logic:** Extracts raw audio to a temporary buffer and transcribes it into segments. Each word is mapped to a micro-second precision timestamp, allowing the frontend to highlight words as they are spoken.

### **Ultralytics YOLO**
- **Optimization:** Uses `half=True` (FP16) and `imgsz=640` for maximum throughput.
- **Grouping:** Sequential detections of the same object are grouped into "Detections" to avoid database pollution and search redundancy.

### **EasyOCR**
- **Execution:** Runs on the same GPU/CPU device as YOLO.
- **Confidence:** Filters out any text with a confidence score < 0.3.

---

## 📊 Performance & Benchmarks

*   **⚡ Search Complexity:** $O(1)$ HashMap lookup for instant timeline mapping.
*   **🕒 Indexing Speed:** Typically under **5 minutes** per video (depends on hardware).
*   **📉 VRAM Optimization:** **50% savings** using FP16 Half-Precision mode.
*   **🚀 CPU Throughput:** **2× speed increase** with YOLOv12n over previous YOLOv8 benchmarks.
*   **🎛️ Scan Rate:** **1 fps** (Optimal) up to **10 fps** (Max accuracy).

---

## 🤝 Contributing & Support

- **Bug Reports:** Open an issue on GitHub.
- **Pull Requests:** Feel free to submit enhancements.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

