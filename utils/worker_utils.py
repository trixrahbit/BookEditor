"""
worker_utils.py - Utilities for managing QThread workers

Provides:
- Safe worker creation and cleanup
- Worker pools
- Progress tracking
- Error handling
"""

from typing import Optional, Callable, Any, List
from PyQt6.QtCore import QThread, QObject, pyqtSignal, QTimer
from dataclasses import dataclass
from enum import Enum
import time


class WorkerState(Enum):
    """Worker state"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class WorkerStats:
    """Worker statistics"""
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    state: WorkerState = WorkerState.IDLE
    errors: int = 0
    tasks_completed: int = 0


class ManagedWorker(QThread):
    """
    Enhanced QThread with built-in management features

    Features:
    - State tracking
    - Statistics
    - Auto-cleanup
    - Error handling
    """

    progress = pyqtSignal(str)  # Status message
    error_occurred = pyqtSignal(str)  # Error message

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stats = WorkerStats(created_at=time.time())
        self._should_stop = False

        # Auto-connect cleanup
        self.finished.connect(self._on_finished)

    def stop(self):
        """Request worker to stop"""
        self._should_stop = True
        self.stats.state = WorkerState.STOPPING

    def should_continue(self) -> bool:
        """Check if worker should continue"""
        return not self._should_stop

    def _on_finished(self):
        """Handle worker finish"""
        self.stats.finished_at = time.time()
        self.stats.state = WorkerState.FINISHED

    def get_elapsed_time(self) -> float:
        """Get elapsed time since start"""
        if self.stats.started_at:
            end_time = self.stats.finished_at or time.time()
            return end_time - self.stats.started_at
        return 0.0

    def log_progress(self, message: str):
        """Log progress message"""
        print(f"[Worker] {message}")
        self.progress.emit(message)

    def log_error(self, error: str):
        """Log error"""
        self.stats.errors += 1
        print(f"[Worker] ERROR: {error}")
        self.error_occurred.emit(error)


class WorkerManager:
    """
    Manager for QThread workers

    Provides safe creation, tracking, and cleanup of workers
    """

    def __init__(self):
        self.active_workers: List[QThread] = []
        self.worker_stats: dict[int, WorkerStats] = {}

    def create_worker(self, worker: QThread) -> QThread:
        """
        Register and return a worker

        Example:
            manager = WorkerManager()
            worker = manager.create_worker(MyWorker())
            worker.finished.connect(lambda: manager.cleanup_worker(worker))
        """
        worker_id = id(worker)
        self.active_workers.append(worker)
        self.worker_stats[worker_id] = WorkerStats(created_at=time.time())

        # Auto-cleanup on finish
        worker.finished.connect(lambda: self._on_worker_finished(worker))

        print(f"[WorkerManager] Created worker {worker_id}")
        return worker

    def cleanup_worker(self, worker: Optional[QThread]) -> None:
        """Safely cleanup a worker"""
        if not worker:
            return

        worker_id = id(worker)
        print(f"[WorkerManager] Cleaning up worker {worker_id}")

        try:
            # Stop if running
            if worker.isRunning():
                worker.quit()
                worker.wait(1000)  # Wait up to 1 second

            # Remove from tracking
            if worker in self.active_workers:
                self.active_workers.remove(worker)

            # Delete
            worker.deleteLater()

            print(f"[WorkerManager] Worker {worker_id} cleaned up")
        except Exception as e:
            print(f"[WorkerManager] Error cleaning worker: {e}")

    def cleanup_all(self):
        """Cleanup all active workers"""
        print(f"[WorkerManager] Cleaning up {len(self.active_workers)} workers")

        for worker in list(self.active_workers):
            self.cleanup_worker(worker)

        self.active_workers.clear()
        print("[WorkerManager] All workers cleaned up")

    def _on_worker_finished(self, worker: QThread):
        """Handle worker finish"""
        worker_id = id(worker)
        if worker_id in self.worker_stats:
            self.worker_stats[worker_id].finished_at = time.time()

    def get_active_count(self) -> int:
        """Get number of active workers"""
        return len(self.active_workers)

    def get_stats(self) -> dict:
        """Get statistics"""
        total_created = len(self.worker_stats)
        total_active = len(self.active_workers)
        total_finished = total_created - total_active

        return {
            'total_created': total_created,
            'active': total_active,
            'finished': total_finished
        }

    def print_stats(self):
        """Print statistics"""
        stats = self.get_stats()
        print("\n[WorkerManager] Statistics:")
        print(f"  Total created: {stats['total_created']}")
        print(f"  Active: {stats['active']}")
        print(f"  Finished: {stats['finished']}")


class WorkerPool:
    """
    Pool of workers for batch processing

    Example:
        pool = WorkerPool(max_workers=3)

        for item in items:
            worker = MyWorker(item)
            pool.add_worker(worker)

        pool.start_all()
        pool.wait_all()
        pool.cleanup_all()
    """

    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.manager = WorkerManager()
        self.pending_workers: List[QThread] = []
        self.running_workers: List[QThread] = []

    def add_worker(self, worker: QThread):
        """Add worker to pool"""
        self.pending_workers.append(worker)

        # Auto-start if under limit
        if len(self.running_workers) < self.max_workers:
            self._start_next()

    def _start_next(self):
        """Start next pending worker"""
        if not self.pending_workers:
            return

        if len(self.running_workers) >= self.max_workers:
            return

        worker = self.pending_workers.pop(0)
        self.manager.create_worker(worker)
        self.running_workers.append(worker)

        # Auto-cleanup and start next on finish
        worker.finished.connect(lambda w=worker: self._on_worker_finished(w))

        worker.start()
        print(f"[WorkerPool] Started worker (running: {len(self.running_workers)})")

    def _on_worker_finished(self, worker: QThread):
        """Handle worker finish"""
        if worker in self.running_workers:
            self.running_workers.remove(worker)

        self.manager.cleanup_worker(worker)

        # Start next pending worker
        self._start_next()

    def start_all(self):
        """Start all workers up to max_workers limit"""
        while self.pending_workers and len(self.running_workers) < self.max_workers:
            self._start_next()

    def wait_all(self):
        """Wait for all workers to finish"""
        for worker in list(self.running_workers):
            if worker.isRunning():
                worker.wait()

    def cleanup_all(self):
        """Cleanup all workers"""
        self.manager.cleanup_all()
        self.pending_workers.clear()
        self.running_workers.clear()

    def get_status(self) -> dict:
        """Get pool status"""
        return {
            'pending': len(self.pending_workers),
            'running': len(self.running_workers),
            'max_workers': self.max_workers
        }


# Convenience functions

_global_manager = WorkerManager()


def create_worker(worker: QThread) -> QThread:
    """Create and register a worker with global manager"""
    return _global_manager.create_worker(worker)


def cleanup_worker(worker: Optional[QThread]) -> None:
    """Cleanup a worker using global manager"""
    _global_manager.cleanup_worker(worker)


def cleanup_all_workers():
    """Cleanup all workers in global manager"""
    _global_manager.cleanup_all()


def get_active_worker_count() -> int:
    """Get number of active workers"""
    return _global_manager.get_active_count()


# Example usage
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys

    print("=== Worker Utils Demo ===\n")

    app = QApplication(sys.argv)


    # Example worker
    class DemoWorker(ManagedWorker):
        def run(self):
            self.stats.started_at = time.time()
            self.stats.state = WorkerState.RUNNING

            for i in range(5):
                if not self.should_continue():
                    break

                self.log_progress(f"Processing item {i + 1}/5")
                time.sleep(0.5)
                self.stats.tasks_completed += 1

            self.log_progress("Complete!")


    # Demo 1: Basic worker management
    print("1. Basic worker management:")
    manager = WorkerManager()

    worker = manager.create_worker(DemoWorker())
    worker.start()
    worker.wait()

    print(f"   Elapsed time: {worker.get_elapsed_time():.2f}s")
    print(f"   Tasks completed: {worker.stats.tasks_completed}")

    manager.cleanup_worker(worker)
    manager.print_stats()

    # Demo 2: Worker pool
    print("\n2. Worker pool (max 2 concurrent):")
    pool = WorkerPool(max_workers=2)

    for i in range(5):
        worker = DemoWorker()
        worker.progress.connect(lambda msg, i=i: print(f"   Worker {i + 1}: {msg}"))
        pool.add_worker(worker)

    pool.start_all()
    pool.wait_all()
    pool.cleanup_all()

    print("\nDone!")