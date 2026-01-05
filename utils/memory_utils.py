"""
memory_utils.py - Memory management utilities for Novelist AI

Provides utilities for:
- Memory cleanup
- Memory monitoring
- Resource management
- Worker cleanup
"""

import gc
import sys
from typing import Optional, Any
from PyQt6.QtCore import QThread


class MemoryManager:
    """Centralized memory management"""

    @staticmethod
    def cleanup():
        """Force garbage collection"""
        collected = gc.collect()
        return collected

    @staticmethod
    def get_memory_usage_mb() -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            # psutil not installed, estimate
            return sys.getsizeof(gc.get_objects()) / 1024 / 1024

    @staticmethod
    def log_memory(prefix: str = ""):
        """Log current memory usage"""
        memory_mb = MemoryManager.get_memory_usage_mb()
        print(f"[Memory] {prefix} {memory_mb:.1f} MB")
        return memory_mb

    @staticmethod
    def check_memory_warning(threshold_mb: float = 500.0) -> bool:
        """Check if memory usage is above threshold"""
        memory_mb = MemoryManager.get_memory_usage_mb()
        if memory_mb > threshold_mb:
            print(f"[Memory] WARNING: High memory usage ({memory_mb:.1f} MB > {threshold_mb} MB)")
            MemoryManager.cleanup()
            return True
        return False

    @staticmethod
    def cleanup_large_objects(*objects):
        """Clean up large objects and force GC"""
        for obj in objects:
            try:
                del obj
            except:
                pass
        gc.collect()

    @staticmethod
    def cleanup_worker(worker: Optional[QThread]) -> None:
        """Safely cleanup a QThread worker"""
        if worker:
            try:
                if worker.isRunning():
                    worker.quit()
                    worker.wait(1000)  # Wait up to 1 second
                worker.deleteLater()
            except Exception as e:
                print(f"[Memory] Error cleaning worker: {e}")
        gc.collect()


class ResourceMonitor:
    """Monitor and manage resources during long operations"""

    def __init__(self, operation_name: str = "Operation", warn_threshold_mb: float = 500.0):
        self.operation_name = operation_name
        self.warn_threshold_mb = warn_threshold_mb
        self.start_memory = 0
        self.iterations = 0

    def start(self):
        """Start monitoring"""
        self.start_memory = MemoryManager.get_memory_usage_mb()
        self.iterations = 0
        print(f"[Monitor] Starting {self.operation_name} - Memory: {self.start_memory:.1f} MB")

    def checkpoint(self, name: str = ""):
        """Log checkpoint with memory usage"""
        self.iterations += 1
        current_memory = MemoryManager.get_memory_usage_mb()
        delta = current_memory - self.start_memory

        checkpoint_name = f"{self.operation_name} - {name}" if name else f"{self.operation_name} #{self.iterations}"
        print(f"[Monitor] {checkpoint_name}: {current_memory:.1f} MB (Δ{delta:+.1f} MB)")

        # Check threshold
        if current_memory > self.warn_threshold_mb:
            print(f"[Monitor] WARNING: Memory above threshold!")
            MemoryManager.cleanup()
            new_memory = MemoryManager.get_memory_usage_mb()
            print(f"[Monitor] After cleanup: {new_memory:.1f} MB")

        return current_memory

    def finish(self):
        """Finish monitoring and cleanup"""
        end_memory = MemoryManager.get_memory_usage_mb()
        delta = end_memory - self.start_memory
        print(f"[Monitor] Finished {self.operation_name}")
        print(f"[Monitor] Start: {self.start_memory:.1f} MB → End: {end_memory:.1f} MB (Δ{delta:+.1f} MB)")
        print(f"[Monitor] Total iterations: {self.iterations}")

        # Final cleanup
        MemoryManager.cleanup()
        final_memory = MemoryManager.get_memory_usage_mb()
        print(f"[Monitor] After cleanup: {final_memory:.1f} MB")


class TextSizeValidator:
    """Validate and manage text sizes"""

    # Size limits in characters
    SMALL_TEXT = 10000  # 10KB
    MEDIUM_TEXT = 50000  # 50KB
    LARGE_TEXT = 100000  # 100KB
    XLARGE_TEXT = 500000  # 500KB

    @staticmethod
    def get_size_category(text: str) -> str:
        """Get size category for text"""
        size = len(text)
        if size < TextSizeValidator.SMALL_TEXT:
            return "small"
        elif size < TextSizeValidator.MEDIUM_TEXT:
            return "medium"
        elif size < TextSizeValidator.LARGE_TEXT:
            return "large"
        elif size < TextSizeValidator.XLARGE_TEXT:
            return "xlarge"
        else:
            return "huge"

    @staticmethod
    def is_safe_size(text: str, max_size: int = LARGE_TEXT) -> bool:
        """Check if text is below safe size"""
        return len(text) <= max_size

    @staticmethod
    def truncate_safe(text: str, max_size: int = LARGE_TEXT) -> tuple[str, bool]:
        """
        Truncate text to safe size if needed
        Returns: (text, was_truncated)
        """
        if len(text) <= max_size:
            return text, False

        print(f"[TextSize] Truncating text from {len(text)} to {max_size} chars")
        return text[:max_size], True

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format size in human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / 1024 / 1024:.1f} MB"


# Convenience functions for common operations

def cleanup_memory() -> int:
    """Quick cleanup - returns number of objects collected"""
    return MemoryManager.cleanup()


def log_memory(prefix: str = "") -> float:
    """Quick memory log - returns memory in MB"""
    return MemoryManager.log_memory(prefix)


def cleanup_worker(worker: Optional[QThread]) -> None:
    """Quick worker cleanup"""
    MemoryManager.cleanup_worker(worker)


def check_high_memory(threshold_mb: float = 500.0) -> bool:
    """Quick memory check - returns True if above threshold"""
    return MemoryManager.check_memory_warning(threshold_mb)


# Decorator for automatic memory cleanup
def with_memory_cleanup(func):
    """Decorator that ensures memory cleanup after function"""

    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            MemoryManager.cleanup()

    return wrapper


# Context manager for resource monitoring
class monitor_resources:
    """Context manager for monitoring resources"""

    def __init__(self, operation_name: str = "Operation"):
        self.monitor = ResourceMonitor(operation_name)

    def __enter__(self):
        self.monitor.start()
        return self.monitor

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.monitor.finish()
        return False


# Example usage:
if __name__ == "__main__":
    print("=== Memory Utils Demo ===\n")

    # Basic usage
    print("1. Basic memory logging:")
    log_memory("Start:")

    # Create some data
    data = ["x" * 1000 for _ in range(1000)]
    log_memory("After creating data:")

    # Cleanup
    del data
    cleanup_memory()
    log_memory("After cleanup:")

    print("\n2. Resource monitoring:")
    with monitor_resources("Demo Operation") as monitor:
        # Do work
        temp = ["x" * 10000 for _ in range(100)]
        monitor.checkpoint("Created temp data")

        # More work
        del temp
        monitor.checkpoint("Deleted temp data")

    print("\n3. Text size validation:")
    small_text = "Hello" * 100
    large_text = "Hello" * 50000

    print(f"Small text: {TextSizeValidator.get_size_category(small_text)}")
    print(f"Large text: {TextSizeValidator.get_size_category(large_text)}")

    truncated, was_truncated = TextSizeValidator.truncate_safe(large_text, 1000)
    print(f"Truncated: {was_truncated}, New size: {len(truncated)}")