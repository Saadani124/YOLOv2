
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ocr import detect_text_in_video
from config import UPLOAD_DIR

video_path = os.path.join(UPLOAD_DIR, "02c04bae-07f0-47c4-b16e-f781c3cf5e61.mp4")

print(f"Testing OCR on: {video_path}")
if not os.path.exists(video_path):
    print("Error: Video file not found")
    sys.exit(1)

results = detect_text_in_video(video_path)
print(f"OCR found {len(results)} results")
for r in results[:10]:
    print(f"[{r['timestamp']:.2f}s] {r['text']} (conf: {r['confidence']:.2f})")
