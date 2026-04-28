"""
OCR Service for ScanVD
Detects visual text in video frames using EasyOCR
"""
from typing import List, Dict, Optional
import cv2
import numpy as np
from config import ENABLE_OCR, OCR_INTERVAL, DEVICE
from core.progress import progress_manager

# Global OCR reader
_ocr_reader = None

def init_ocr_model():
    """
    Initialize the EasyOCR reader.
    """
    global _ocr_reader
    
    if not ENABLE_OCR:
        print("⚠️  OCR is disabled in config")
        return None
    
    if _ocr_reader is None:
        try:
            print(f"Initializing EasyOCR reader on {DEVICE.upper()}...")
            import easyocr
            # We only use 'en' by default, can be expanded
            use_gpu = (DEVICE == 'cuda')
            _ocr_reader = easyocr.Reader(['en'], gpu=use_gpu)
            print("✓ EasyOCR reader loaded successfully!")
        except Exception as e:
            print(f"❌ Failed to load EasyOCR: {e}")
            return None
            
    return _ocr_reader


def detect_text_in_video(video_path: str, fps: float = None, task_id: str = None) -> List[Dict]:
    """
    Extract frames from video and run OCR on them.
    
    Args:
        video_path: Path to the video file
        fps: Frames per second of the video (optional)
        task_id: Progress manager task ID for updates
        
    Returns:
        List of detection dictionaries
    """
    if not ENABLE_OCR:
        return []
        
    reader = init_ocr_model()
    if not reader:
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
                
                # Convert BGR to RGB for EasyOCR
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Run OCR
                results = reader.readtext(rgb_frame)
                
                # Extract detections
                for (bbox, text, prob) in results:
                    if prob >= 0.4: # Only keep reasonable confidence
                        # bbox is [ [top_left], [top_right], [bottom_right], [bottom_left] ]
                        # x, y coords
                        x_coords = [p[0] for p in bbox]
                        y_coords = [p[1] for p in bbox]
                        x1, x2 = min(x_coords), max(x_coords)
                        y1, y2 = min(y_coords), max(y_coords)
                        
                        detections.append({
                            "frame_number": frame_number,
                            "timestamp": timestamp,
                            "text": text,
                            "confidence": float(prob),
                            "bbox": {
                                "x": float(x1),
                                "y": float(y1),
                                "width": float(x2 - x1),
                                "height": float(y2 - y1)
                            }
                        })
                
                processed_frames += 1
                if task_id:
                    progress = (processed_frames / total_to_process) * 100
                    message = f"Scanning text in frame {frame_number}/{total_frames}..."
                    progress_manager.update_progress(task_id, "ocr", min(progress, 99), message)
                    
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
