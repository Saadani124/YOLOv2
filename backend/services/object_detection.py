"""
Object Detection Service for ScanVD
Detects objects in video frames using YOLO
"""
from typing import List, Dict, Optional
import cv2
import numpy as np
from config import ENABLE_OBJECT_DETECTION, OBJECT_DETECTION_MODEL, OBJECT_DETECTION_INTERVAL, DEVICE
from core.progress import progress_manager

# Global detection model
_detection_model = None


def init_detection_model():
    """
    Initialize the object detection model.
    Uses YOLOv12 (turbo) for fast and accurate detection (NeurIPS 2025 attention-centric model).
    """
    global _detection_model
    
    if not ENABLE_OBJECT_DETECTION:
        print("⚠️  Object detection is disabled in config")
        return None
    
    try:
        import torch
        from ultralytics import YOLO
        
        print(f"Loading object detection model: {OBJECT_DETECTION_MODEL} on device: {DEVICE}")
        
        # PyTorch 2.6+ security fix: Automatically handle the new weights_only=True default
        # which blocks unpickling custom classes from ultralytics
        original_load = torch.load
        def patched_load(*args, **kwargs):
            if 'weights_only' not in kwargs:
                kwargs['weights_only'] = False
            return original_load(*args, **kwargs)
        
        torch.load = patched_load
        try:
            _detection_model = YOLO(OBJECT_DETECTION_MODEL)
            _detection_model.to(DEVICE)
        finally:
            # Restore original torch.load to avoid side effects elsewhere
            torch.load = original_load
            
        print("✓ Object detection model loaded successfully!")
        
        return _detection_model
        
    except ImportError:
        print("⚠️  ultralytics not installed. Install with: pip install ultralytics")
        return None
    except Exception as e:
        print(f"⚠️  Error loading detection model: {e}")
        # Provide helpful hint for PyTorch 2.6 users if they still hit it
        if "weights_only" in str(e) or "WeightsUnpickler" in str(e):
            print("💡 Hint: This appears to be a PyTorch 2.6 security restriction. Ensure 'ultralytics' is up to date (pip install -U ultralytics).")
        return None


def detect_objects_in_video(video_path: str, fps: Optional[float] = None, task_id: Optional[str] = None) -> Optional[List[Dict]]:
    """
    Detect objects throughout a video file.
    
    Args:
        video_path: Path to the video file
        fps: Video FPS (if known, otherwise will be detected)
        task_id: Optional task ID for progress reporting
        
    Returns:
        List of detection dictionaries with timestamps and object info
    """
    if _detection_model is None:
        return None
    
    try:
        if task_id:
            progress_manager.update_progress(task_id, "detecting", 0, "Initializing object detection...")
        
        print(f"Performing object detection on video...")
        
        # Open video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("⚠️  Failed to open video file")
            return None
        
        # Get video properties
        if fps is None:
            fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Calculate frame interval (process every N frames)
        frame_interval = int(fps * OBJECT_DETECTION_INTERVAL)
        total_to_process = total_frames // frame_interval if frame_interval > 0 else 1
        
        if task_id:
            progress_manager.add_log(task_id, f"  Video FPS: {fps:.2f}")
            progress_manager.add_log(task_id, f"  Total frames: {total_frames}")
            progress_manager.add_log(task_id, f"  Processing every {frame_interval} frames ({OBJECT_DETECTION_INTERVAL}s interval)")
        
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
                
                # Run detection with optimized parameters
                results = _detection_model(
                    frame, 
                    verbose=False,
                    device=DEVICE,
                    half=(DEVICE == "cuda"), # Use FP16 if on GPU for massive speedup
                    imgsz=640,               # Standard optimal size
                    conf=0.45,               # Filter low confidence early to save CPU
                    iou=0.45                 # Standard NMS threshold
                )
                
                # Extract detections
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        # Get box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        
                        # Get confidence and class
                        confidence = float(box.conf[0].cpu().numpy())
                        class_id = int(box.cls[0].cpu().numpy())
                        class_name = result.names[class_id]
                        
                        # Only keep high-confidence detections
                        if confidence >= 0.5:
                            detections.append({
                                "frame_number": frame_number,
                                "timestamp": timestamp,
                                "object_class": class_name,
                                "confidence": confidence,
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
                    message = f"Analyzing frame {frame_number}/{total_frames}..."
                    progress_manager.update_progress(task_id, "detecting", min(progress, 99), message)
                    
                    # Every 10% or so, add a log line
                    if processed_frames % max(1, (total_to_process // 10)) == 0:
                        progress_manager.add_log(task_id, f"  Progress: {progress:.1f}% ({len(detections)} objects detected)")
            
            frame_number += 1
        
        cap.release()
        
        # Get unique object classes
        unique_objects = set(d["object_class"] for d in detections)
        if task_id:
            progress_manager.add_log(task_id, "✓ Object detection complete!")
            progress_manager.add_log(task_id, f"  Total detections: {len(detections)}")
            progress_manager.add_log(task_id, f"  Unique objects: {len(unique_objects)}")
            progress_manager.add_log(task_id, f"  Objects found: {', '.join(sorted(unique_objects))}")
            progress_manager.update_progress(task_id, "detecting", 100, "Object detection complete!")
        
        return detections
        
    except Exception as e:
        print(f"⚠️  Object detection failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def search_objects(detections: List[Dict], query: str, threshold: float = 0.6) -> List[Dict]:
    """
    Search for specific objects in detection results.
    
    Args:
        detections: List of detection dictionaries
        query: Object class to search for (e.g., "car", "person")
        threshold: Minimum confidence threshold
        
    Returns:
        Filtered and grouped detection results
    """
    query_lower = query.lower().strip()
    
    # Filter detections by query
    matches = []
    for detection in detections:
        object_class = detection["object_class"].lower()
        
        # Exact match or partial match
        if query_lower == object_class or query_lower in object_class:
            if detection["confidence"] >= threshold:
                matches.append(detection)
    
    # Do not group: return each detection as a separate result
    formatted_matches = []
    for m in matches:
        formatted_matches.append({
            "object_class": m["object_class"],
            "start_time": m["timestamp"],
            "end_time": m["timestamp"],
            "duration": 0.0,
            "confidence": m["confidence"],
            "frame_count": 1,
            "bbox": m.get("bbox")
        })
        
    return formatted_matches


def _group_detections(detections: List[Dict], time_threshold: float = 10.0) -> List[Dict]:
    """
    Group detections that are close in time (likely same object).
    
    Args:
        detections: List of detections
        time_threshold: Maximum time gap to consider same occurrence (seconds)
        
    Returns:
        List of grouped detection occurrences
    """
    if not detections:
        return []
    
    # Sort by timestamp
    sorted_detections = sorted(detections, key=lambda x: x["timestamp"])
    
    groups = []
    current_group = [sorted_detections[0]]
    
    for detection in sorted_detections[1:]:
        # Check if this detection is close to the previous one
        time_diff = detection["timestamp"] - current_group[-1]["timestamp"]
        
        if time_diff <= time_threshold:
            # Same occurrence
            current_group.append(detection)
        else:
            # New occurrence - save current group
            groups.append(_merge_group(current_group))
            current_group = [detection]
    
    # Add last group
    if current_group:
        groups.append(_merge_group(current_group))
    
    return groups


def _merge_group(group: List[Dict]) -> Dict:
    """
    Merge a group of detections into a single occurrence.
    
    Args:
        group: List of detections from same occurrence
        
    Returns:
        Merged detection with start/end times
    """
    return {
        "object_class": group[0]["object_class"],
        "start_time": group[0]["timestamp"],
        "end_time": group[-1]["timestamp"],
        "duration": group[-1]["timestamp"] - group[0]["timestamp"],
        "confidence": np.mean([d["confidence"] for d in group]),
        "frame_count": len(group),
        "first_frame": group[0]["frame_number"],
        "bbox": group[0]["bbox"]  # Use first detection's bbox
    }


def get_detection_statistics(detections: List[Dict]) -> Dict[str, Dict]:
    """
    Get statistics about detected objects.
    
    Args:
        detections: List of all detections
        
    Returns:
        Dictionary with statistics per object class
    """
    stats = {}
    
    for detection in detections:
        obj_class = detection["object_class"]
        
        if obj_class not in stats:
            stats[obj_class] = {
                "count": 0,
                "total_duration": 0.0,
                "avg_confidence": []
            }
        
        stats[obj_class]["count"] += 1
        stats[obj_class]["total_duration"] += detection.get("duration", 0)
        stats[obj_class]["avg_confidence"].append(detection["confidence"])
    
    # Calculate averages
    for obj_class in stats:
        confidences = stats[obj_class]["avg_confidence"]
        stats[obj_class]["avg_confidence"] = np.mean(confidences) if confidences else 0.0
    
    return stats


# Initialize model on module load
init_detection_model()