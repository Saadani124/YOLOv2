"""
OCR Service for ScanVD
Detects visual text in video frames using Tesseract OCR (via pytesseract)
"""
from typing import List, Dict, Optional
import cv2
import numpy as np
import pytesseract
from config import ENABLE_OCR, OCR_INTERVAL
from core.progress import progress_manager

# Note: On Windows, you may need to point to the tesseract executable:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def init_ocr_model():
    """
    Check if Tesseract is available.
    """
    if not ENABLE_OCR:
        print("⚠️  OCR is disabled in config")
        return False
    
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✓ Tesseract OCR detected (version {version})")
        return True
    except Exception as e:
        print(f"❌ Tesseract OCR not found or not in PATH: {e}")
        print("   Please install Tesseract OCR and add it to your PATH.")
        return False


def detect_text_in_video(video_path: str, fps: float = None, task_id: str = None) -> List[Dict]:
    """
    Extract frames from video and run Tesseract OCR on them.
    
    Args:
        video_path: Path to the video file
        fps: Frames per second of the video (optional)
        task_id: Progress manager task ID for updates
        
    Returns:
        List of detection dictionaries
    """
    if not ENABLE_OCR:
        return []
        
    is_available = init_ocr_model()
    if not is_available:
        if task_id:
            progress_manager.add_log(task_id, "⚠️ OCR Skipped: Tesseract not found on system.")
        return []
        
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Could not open video file")
        
        # Get video properties
        if fps is None:
            fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Calculate frame interval (process every N frames)
        frame_interval = int(fps * OCR_INTERVAL)
        total_to_process = total_frames // frame_interval if frame_interval > 0 else 1
        
        if task_id:
            progress_manager.add_log(task_id, f"  OCR Processing every {frame_interval} frames ({OCR_INTERVAL}s interval)")
        
        detections = []
        processed_frames = 0
        
        for i in range(total_to_process):
            target_frame = i * frame_interval
            if target_frame >= total_frames:
                break
                
            # Seek to target frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = target_frame / fps
            
            # Convert BGR to RGB for Tesseract
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Run OCR using image_to_data for bbox and confidence
            data = pytesseract.image_to_data(rgb_frame, output_type=pytesseract.Output.DICT)
            
            # Extract detections
            for j in range(len(data['text'])):
                text = data['text'][j].strip()
                conf = float(data['conf'][j])
                
                if text and conf >= 40: # Tesseract confidence is 0-100
                    detections.append({
                        "frame_number": target_frame,
                        "timestamp": timestamp,
                        "text": text,
                        "confidence": conf / 100.0,
                        "bbox": {
                            "x": float(data['left'][j]),
                            "y": float(data['top'][j]),
                            "width": float(data['width'][j]),
                            "height": float(data['height'][j])
                        }
                    })
            
            processed_frames += 1
            if task_id:
                progress = (processed_frames / total_to_process) * 100
                message = f"Scanning text in frame {target_frame}/{total_frames}..."
                progress_manager.update_progress(task_id=task_id, stage="indexing", progress=min(progress, 99), message=message)
                
                if processed_frames % max(1, (total_to_process // 10)) == 0:
                    progress_manager.add_log(task_id, f"  OCR Progress: {progress:.1f}% ({len(detections)} words found)")
        
        cap.release()
        
        if task_id:
            progress_manager.add_log(task_id, f"✓ OCR complete: {len(detections)} total words found")
            
        return detections
        
    except Exception as e:
        print(f"Error in OCR: {e}")
        import traceback
        traceback.print_exc()
        return []
