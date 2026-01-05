"""
rate_limiter.py - Rate limiting utilities for API calls

Prevents API overload by:
- Tracking request timing
- Enforcing delays between calls
- Managing request queues
- Monitoring API usage
"""

import time
from typing import Optional, Callable, Any
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class RateLimit:
    """Rate limit configuration"""
    requests_per_minute: int = 20
    requests_per_hour: int = 100
    min_delay_seconds: float = 2.0


class RateLimiter:
    """
    Rate limiter for API calls

    Example:
        limiter = RateLimiter(requests_per_minute=20)

        for item in items:
            limiter.wait_if_needed()
            result = api_call(item)
            limiter.record_request()
    """

    def __init__(
            self,
            requests_per_minute: int = 20,
            requests_per_hour: int = 100,
            min_delay_seconds: float = 2.0
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.min_delay_seconds = min_delay_seconds

        # Track recent requests
        self.recent_requests = deque(maxlen=requests_per_hour)
        self.last_request_time: Optional[float] = None

        # Statistics
        self.total_requests = 0
        self.total_wait_time = 0.0
        self.start_time = time.time()

    def record_request(self):
        """Record a request"""
        now = time.time()
        self.recent_requests.append(now)
        self.last_request_time = now
        self.total_requests += 1

    def get_requests_in_window(self, window_seconds: int) -> int:
        """Get number of requests in the last N seconds"""
        now = time.time()
        cutoff = now - window_seconds
        return sum(1 for req_time in self.recent_requests if req_time > cutoff)

    def calculate_delay(self) -> float:
        """Calculate how long to wait before next request"""
        now = time.time()
        delays = []

        # Check minimum delay
        if self.last_request_time:
            time_since_last = now - self.last_request_time
            if time_since_last < self.min_delay_seconds:
                delays.append(self.min_delay_seconds - time_since_last)

        # Check per-minute limit
        requests_last_minute = self.get_requests_in_window(60)
        if requests_last_minute >= self.requests_per_minute:
            # Find oldest request in last minute
            cutoff = now - 60
            oldest_in_window = min(
                (t for t in self.recent_requests if t > cutoff),
                default=now
            )
            delay_until_minute_resets = 60 - (now - oldest_in_window)
            if delay_until_minute_resets > 0:
                delays.append(delay_until_minute_resets)

        # Check per-hour limit
        requests_last_hour = self.get_requests_in_window(3600)
        if requests_last_hour >= self.requests_per_hour:
            # Find oldest request in last hour
            cutoff = now - 3600
            oldest_in_window = min(
                (t for t in self.recent_requests if t > cutoff),
                default=now
            )
            delay_until_hour_resets = 3600 - (now - oldest_in_window)
            if delay_until_hour_resets > 0:
                delays.append(delay_until_hour_resets)

        return max(delays) if delays else 0.0

    def wait_if_needed(self) -> float:
        """
        Wait if rate limit would be exceeded
        Returns: seconds waited
        """
        delay = self.calculate_delay()

        if delay > 0:
            print(f"[RateLimit] Waiting {delay:.1f} seconds...")
            time.sleep(delay)
            self.total_wait_time += delay

        return delay

    def can_make_request(self) -> bool:
        """Check if a request can be made without waiting"""
        return self.calculate_delay() == 0

    def get_stats(self) -> dict:
        """Get usage statistics"""
        elapsed = time.time() - self.start_time

        return {
            'total_requests': self.total_requests,
            'total_wait_time': self.total_wait_time,
            'elapsed_time': elapsed,
            'requests_per_minute': self.total_requests / (elapsed / 60) if elapsed > 0 else 0,
            'requests_last_minute': self.get_requests_in_window(60),
            'requests_last_hour': self.get_requests_in_window(3600),
            'time_until_next_allowed': self.calculate_delay()
        }

    def print_stats(self):
        """Print usage statistics"""
        stats = self.get_stats()
        print("\n[RateLimit] Statistics:")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Total wait time: {stats['total_wait_time']:.1f}s")
        print(f"  Elapsed time: {stats['elapsed_time']:.1f}s")
        print(f"  Avg requests/min: {stats['requests_per_minute']:.1f}")
        print(f"  Requests (last min): {stats['requests_last_minute']}")
        print(f"  Requests (last hour): {stats['requests_last_hour']}")

    def reset(self):
        """Reset the rate limiter"""
        self.recent_requests.clear()
        self.last_request_time = None
        self.total_requests = 0
        self.total_wait_time = 0.0
        self.start_time = time.time()


class AdaptiveRateLimiter(RateLimiter):
    """
    Rate limiter that adapts based on errors

    Automatically slows down when errors occur,
    speeds up when requests succeed.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.error_count = 0
        self.success_count = 0
        self.current_delay_multiplier = 1.0

    def record_success(self):
        """Record a successful request"""
        self.record_request()
        self.success_count += 1

        # Gradually speed up after successes
        if self.success_count % 10 == 0:
            self.current_delay_multiplier = max(0.5, self.current_delay_multiplier * 0.9)
            print(f"[AdaptiveRate] Speeding up: delay multiplier = {self.current_delay_multiplier:.2f}")

    def record_error(self):
        """Record a failed request"""
        self.error_count += 1

        # Slow down after errors
        self.current_delay_multiplier = min(5.0, self.current_delay_multiplier * 1.5)
        print(f"[AdaptiveRate] Slowing down: delay multiplier = {self.current_delay_multiplier:.2f}")

    def calculate_delay(self) -> float:
        """Calculate delay with adaptive multiplier"""
        base_delay = super().calculate_delay()
        return base_delay * self.current_delay_multiplier


def rate_limited(limiter: RateLimiter):
    """
    Decorator to rate-limit a function

    Example:
        limiter = RateLimiter(requests_per_minute=20)

        @rate_limited(limiter)
        def api_call(data):
            return requests.post(url, data=data)
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            limiter.wait_if_needed()
            result = func(*args, **kwargs)
            limiter.record_request()
            return result

        return wrapper

    return decorator


# Example usage
if __name__ == "__main__":
    print("=== Rate Limiter Demo ===\n")

    # Basic rate limiter
    print("1. Basic rate limiting:")
    limiter = RateLimiter(
        requests_per_minute=5,  # Low for demo
        min_delay_seconds=1.0
    )

    for i in range(8):
        print(f"\nRequest {i + 1}:")
        limiter.wait_if_needed()
        print("  Making request...")
        limiter.record_request()

        stats = limiter.get_stats()
        print(f"  Requests in last minute: {stats['requests_last_minute']}")

    limiter.print_stats()

    # Adaptive rate limiter
    print("\n\n2. Adaptive rate limiting:")
    adaptive = AdaptiveRateLimiter(requests_per_minute=10)

    # Simulate some successes
    for i in range(5):
        adaptive.wait_if_needed()
        adaptive.record_success()
        print(f"Success {i + 1}")

    # Simulate an error
    adaptive.record_error()
    print("Error occurred!")

    # Continue
    for i in range(3):
        adaptive.wait_if_needed()
        adaptive.record_success()
        print(f"Success {i + 6}")

    adaptive.print_stats()