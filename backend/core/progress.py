import time
import json
import asyncio
from typing import Dict, Optional, Any

class ProgressManager:
    """
    Manages real-time progress for background tasks.
    Supports streaming via Server-Sent Events (SSE).
    """
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def start_task(self, task_id: str, message: str = "Starting..."):
        self.tasks[task_id] = {
            "status": "running",
            "stage": "starting",
            "progress": 0,
            "message": message,
            "logs": [f"[INFO] {message}"],
            "last_updated": time.time(),
            "error": None,
            "queues": []  # SSE subscriber queues live here
        }

    def _broadcast(self, task_id: str, update: dict):
        """Send an update to all subscriber queues for a task (thread-safe)."""
        if task_id not in self.tasks:
            return
        data = json.dumps(update)
        for q in list(self.tasks[task_id]["queues"]):
            try:
                # Use call_soon_threadsafe for cross-thread safety
                loop = asyncio.get_event_loop()
                loop.call_soon_threadsafe(q.put_nowait, data)
            except RuntimeError:
                # No running event loop — fall back to direct put
                try:
                    q.put_nowait(data)
                except Exception:
                    pass
            except Exception:
                pass


    def add_log(self, task_id: str, log_message: str):
        """Add a terminal-style log message for the task."""
        if task_id not in self.tasks:
            return
        
        self.tasks[task_id]["logs"].append(log_message)
        self.tasks[task_id]["last_updated"] = time.time()
        
        self._broadcast(task_id, {
            "task_id": task_id,
            "status": self.tasks[task_id]["status"],
            "stage": self.tasks[task_id]["stage"],
            "progress": self.tasks[task_id]["progress"],
            "message": self.tasks[task_id]["message"],
            "new_log": log_message,
            "timestamp": time.time()
        })

    def update_progress(self, task_id: str, stage: str, progress: float, message: str = None):
        """Update the progress of a specific task and notify subscribers."""
        if task_id not in self.tasks:
            return

        self.tasks[task_id]["stage"] = stage
        self.tasks[task_id]["progress"] = progress
        if message:
            self.tasks[task_id]["message"] = message
            self.add_log(task_id, f"[INFO] {message}")
            
        self.tasks[task_id]["last_updated"] = time.time()

        self._broadcast(task_id, {
            "task_id": task_id,
            "status": self.tasks[task_id]["status"],
            "stage": stage,
            "progress": progress,
            "message": self.tasks[task_id]["message"],
            "timestamp": time.time()
        })

    def set_error(self, task_id: str, error_message: str):
        if task_id not in self.tasks:
            self.start_task(task_id)
        
        self.tasks[task_id].update({
            "status": "failed",
            "error": error_message,
            "last_updated": time.time()
        })
        self.add_log(task_id, f"[ERROR] {error_message}")

    def complete_task(self, task_id: str, message: str = "Complete"):
        if task_id in self.tasks:
            self.tasks[task_id].update({
                "stage": "done",
                "progress": 100.0,
                "message": message,
                "status": "completed",
                "last_updated": time.time()
            })
            self.add_log(task_id, f"✓ {message}")
            
            # Send final completion event
            self._broadcast(task_id, {
                "task_id": task_id,
                "status": "completed",
                "stage": "done",
                "progress": 100.0,
                "message": message,
                "timestamp": time.time()
            })

    async def subscribe(self, task_id: str):
        """SSE generator that yields progress updates for a task."""
        queue = asyncio.Queue()
        
        # Register this subscriber's queue in the task's queue list
        if task_id in self.tasks:
            self.tasks[task_id]["queues"].append(queue)
        else:
            # Task hasn't started yet — create a placeholder so the queue is ready
            self.start_task(task_id, "Waiting for processing to begin...")
            self.tasks[task_id]["queues"].append(queue)
        
        # Send current state immediately
        initial_state = {
            "task_id": task_id,
            "status": self.tasks[task_id]["status"],
            "stage": self.tasks[task_id]["stage"],
            "progress": self.tasks[task_id]["progress"],
            "message": self.tasks[task_id]["message"],
            "logs": self.tasks[task_id]["logs"],
            "timestamp": time.time()
        }
        yield f"data: {json.dumps(initial_state)}\n\n"
        
        # If the task is already completed/failed, stop immediately
        if self.tasks[task_id]["status"] in ["completed", "failed"]:
            return
        
        try:
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
                
                # Stop streaming after completion or failure
                parsed = json.loads(data)
                if parsed.get("status") in ["completed", "failed"]:
                    break
        finally:
            # Cleanup: remove this queue from the task
            if task_id in self.tasks and queue in self.tasks[task_id]["queues"]:
                self.tasks[task_id]["queues"].remove(queue)

# Global instance
progress_manager = ProgressManager()
