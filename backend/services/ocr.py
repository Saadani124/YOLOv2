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
        frame_number = 0
        processed_frames = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame at intervals
            if frame_number % frame_interval == 0:
                timestamp = frame_number / fps
                
                # Convert BGR to RGB for Tesseract
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Run OCR using image_to_data for bbox and confidence
                # Output is a dictionary with keys: level, page_num, block_num, par_num, line_num, word_num, left, top, width, height, conf, text
                data = pytesseract.image_to_data(rgb_frame, output_type=pytesseract.Output.DICT)
                
                # Extract detections
                for i in range(len(data['text'])):
                    text = data['text'][i].strip()
                    conf = float(data['conf'][i])
                    
                    if text and conf >= 40: # Tesseract confidence is 0-100, we use 40 as threshold
                        detections.append({
                            "frame_number": frame_number,
                            "timestamp": timestamp,
                            "text": text,
                            "confidence": conf / 100.0, # Convert to 0.0-1.0 scale
                            "bbox": {
                                "x": float(data['left'][i]),
                                "y": float(data['top'][i]),
                                "width": float(data['width'][i]),
                                "height": float(data['height'][i])
                            }
                        })
                
                processed_frames += 1
                if task_id:
                    progress = (processed_frames / total_to_process) * 100
                    message = f"Scanning text in frame {frame_number}/{total_frames}..."
                    progress_manager.update_progress(video_id=task_id, step="indexing", percentage=min(progress, 99), message=message)
                    
                    if processed_frames % max(1, (total_to_process // 10)) == 0:
                        progress_manager.add_log(task_id, f"  OCR Progress: {progress:.1f}% ({len(detections)} words found)")
            
            frame_number += 1
        
        cap.release()
        
        if task_id:
            progress_manager.add_log(task_id, f"✓ OCR complete: {len(detections)} total words found")
            
        return detections
        
    except Exception as e:
        print(f"Error in OCR: {e}")
        import traceback
        traceback.print_exc()
        return []
