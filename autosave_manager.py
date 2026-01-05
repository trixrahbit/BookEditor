from PyQt6.QtCore import QTimer, QObject, pyqtSignal


class AutoSaveManager(QObject):
    """Manages autosave with debouncing to prevent lag"""
    
    save_triggered = pyqtSignal()  # Signal when save should happen
    saving_started = pyqtSignal()
    saving_finished = pyqtSignal()
    
    def __init__(self, parent=None, delay_ms=1000):
        """
        Initialize autosave manager
        
        Args:
            parent: Parent QObject
            delay_ms: Delay in milliseconds before saving (default 1000ms = 1 second)
        """
        super().__init__(parent)
        self.delay_ms = delay_ms
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._do_save)
        self.pending_save = False
    
    def request_save(self):
        """Request a save - will be debounced"""
        # Restart the timer - if user keeps typing, this delays the save
        self.save_timer.stop()
        self.save_timer.start(self.delay_ms)
        self.pending_save = True
    
    def save_immediately(self):
        """Force immediate save (when switching scenes, etc)"""
        self.save_timer.stop()
        if self.pending_save:
            self._do_save()
    
    def _do_save(self):
        """Internal: Actually trigger the save"""
        if self.pending_save:
            print("AutoSave: Triggering save...")
            self.saving_started.emit()  # Can show "Saving..." indicator
            self.save_triggered.emit()
            self.saving_finished.emit()  # Can show "Saved!" indicator
            self.pending_save = False
    
    def has_pending_save(self) -> bool:
        """Check if there's a pending save"""
        return self.pending_save