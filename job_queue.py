# job_queue.py
import uuid
import traceback
from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional, List

from PyQt6.QtCore import QObject, QThread, pyqtSignal, QMutex, QWaitCondition


@dataclass
class Job:
    id: str
    kind: str  # "chapter_timeline", "book_bible", etc.
    payload: Dict[str, Any]
    on_done: Optional[Callable[[Dict[str, Any]], None]] = None
    on_error: Optional[Callable[[str], None]] = None


class JobQueueWorker(QThread):
    job_started = pyqtSignal(str, str)   # job_id, kind
    job_finished = pyqtSignal(str, str)  # job_id, kind
    job_failed = pyqtSignal(str, str, str)  # job_id, kind, error

    def __init__(self, runner: Callable[[Job], Dict[str, Any]]):
        super().__init__()
        self._runner = runner
        self._mutex = QMutex()
        self._cond = QWaitCondition()
        self._queue: List[Job] = []
        self._stopped = False

    def enqueue(self, job: Job) -> None:
        self._mutex.lock()
        try:
            self._queue.append(job)
            self._cond.wakeAll()
        finally:
            self._mutex.unlock()

    def stop(self):
        self._mutex.lock()
        try:
            self._stopped = True
            self._cond.wakeAll()
        finally:
            self._mutex.unlock()

    def run(self):
        while True:
            self._mutex.lock()
            try:
                while not self._queue and not self._stopped:
                    self._cond.wait(self._mutex)

                if self._stopped:
                    return

                job = self._queue.pop(0)
            finally:
                self._mutex.unlock()

            self.job_started.emit(job.id, job.kind)
            try:
                result = self._runner(job)
                if job.on_done:
                    job.on_done(result)
                self.job_finished.emit(job.id, job.kind)
            except Exception as e:
                traceback.print_exc()
                msg = str(e)
                if job.on_error:
                    job.on_error(msg)
                self.job_failed.emit(job.id, job.kind, msg)


def new_job(kind: str, payload: Dict[str, Any], on_done=None, on_error=None) -> Job:
    return Job(id=str(uuid.uuid4()), kind=kind, payload=payload, on_done=on_done, on_error=on_error)
