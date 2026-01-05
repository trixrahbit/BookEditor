"""
Simple job queue for background analysis tasks
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import Callable, Dict, Any, List
from dataclasses import dataclass
import queue
import time


@dataclass
class Job:
    """Represents a background job"""
    kind: str
    payload: Dict[str, Any]


def new_job(kind: str, payload: Dict[str, Any]) -> Job:
    """Create a new job"""
    return Job(kind=kind, payload=payload)


class JobQueueWorker(QThread):
    """Background worker that processes queued jobs"""

    job_started = pyqtSignal(str)  # job kind
    job_finished = pyqtSignal(str, object)  # job kind, result
    job_error = pyqtSignal(str, str)  # job kind, error

    def __init__(self, job_runner: Callable[[Job], Dict[str, Any]]):
        super().__init__()
        self.job_runner = job_runner
        self.job_queue = queue.Queue()
        self.running = True
        self.current_job = None
        self.jobs_processed = 0
        self.max_jobs_before_cleanup = 50  # Prevent memory buildup

    def enqueue(self, job: Job):
        """Add job to queue"""
        self.job_queue.put(job)
        print(f"Enqueued job: {job.kind} (Queue size: {self.job_queue.qsize()})")

    def run(self):
        """Process jobs from queue"""
        print("JobQueueWorker started")

        while self.running:
            try:
                # Wait for job with timeout
                try:
                    job = self.job_queue.get(timeout=0.5)
                except queue.Empty:
                    # No jobs, continue loop
                    continue

                self.current_job = job
                print(f"Processing job: {job.kind}")
                self.job_started.emit(job.kind)

                try:
                    result = self.job_runner(job)
                    self.job_finished.emit(job.kind, result)
                    print(f"Job completed: {job.kind}")
                    self.jobs_processed += 1

                except Exception as e:
                    import traceback
                    print(f"Job failed: {job.kind}")
                    traceback.print_exc()
                    self.job_error.emit(job.kind, str(e))

                finally:
                    self.current_job = None
                    self.job_queue.task_done()

                    # Periodic cleanup to prevent memory buildup
                    if self.jobs_processed >= self.max_jobs_before_cleanup:
                        print(f"Cleanup: Processed {self.jobs_processed} jobs")
                        self.jobs_processed = 0
                        time.sleep(0.1)  # Brief pause

            except Exception as e:
                print(f"Worker error: {e}")
                import traceback
                traceback.print_exc()

        print("JobQueueWorker stopped")

    def stop(self):
        """Stop the worker gracefully"""
        print("Stopping JobQueueWorker...")
        self.running = False

        # Cancel current job if any
        if self.current_job:
            print(f"Cancelling current job: {self.current_job.kind}")

        # Clear remaining queue
        while not self.job_queue.empty():
            try:
                self.job_queue.get_nowait()
                self.job_queue.task_done()
            except queue.Empty:
                break

    def wait_for_completion(self, timeout: float = 10.0):
        """Wait for all queued jobs to complete"""
        start = time.time()
        while not self.job_queue.empty():
            if time.time() - start > timeout:
                print(f"Timeout waiting for jobs to complete ({self.job_queue.qsize()} remaining)")
                return False
            time.sleep(0.1)
        return True

    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.job_queue.qsize()