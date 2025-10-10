"""
Enhanced rate limiting and retry logic for Spotify API requests.
This module provides intelligent handling of API rate limits with exponential backoff,
batch processing, and adaptive retry strategies.
"""

import asyncio
import logging
import random
import time
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from functools import wraps
import requests

__all__ = [
    "RateLimiter",
    "RateLimitError", 
    "ExponentialBackoff",
    "adaptive_retry",
    "batch_processor"
]

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class ExponentialBackoff:
    """Implements exponential backoff with jitter for API requests."""
    
    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 300.0,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        
    def calculate_delay(self, attempt: int, retry_after: Optional[int] = None) -> float:
        """Calculate the delay for the given attempt number."""
        if retry_after:
            # If server tells us when to retry, respect it with some buffer
            return min(retry_after + random.uniform(1, 5), self.max_delay)
            
        # Calculate exponential backoff
        delay = self.base_delay * (self.backoff_factor ** attempt)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            delay *= (0.5 + random.random())
            
        return min(delay, self.max_delay)


class RateLimiter:
    """
    Advanced rate limiter with multiple strategies for handling API limits.
    """
    
    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_limit: int = 100,
        cooldown_factor: float = 0.5
    ):
        self.requests_per_second = requests_per_second
        self.burst_limit = burst_limit
        self.cooldown_factor = cooldown_factor
        
        # Track request timing
        self.request_times: list[float] = []
        self.is_cooling_down = False
        self.cooldown_until = 0.0
        
        # Track rate limit state
        self.consecutive_rate_limits = 0
        self.last_rate_limit_time = 0.0
        
    async def acquire(self) -> None:
        """Acquire permission to make a request."""
        current_time = time.time()
        
        # Check if we're in cooldown period
        if self.is_cooling_down and current_time < self.cooldown_until:
            wait_time = self.cooldown_until - current_time
            logger.debug(f"Rate limiter cooling down, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            current_time = time.time()
            
        # Remove old request times (older than 1 second)
        self.request_times = [
            req_time for req_time in self.request_times 
            if current_time - req_time < 1.0
        ]
        
        # Check if we need to wait before making request
        if len(self.request_times) >= self.requests_per_second:
            sleep_time = 1.0 / self.requests_per_second
            await asyncio.sleep(sleep_time)
            
        # Record this request
        self.request_times.append(time.time())
        
    def handle_rate_limit(self, retry_after: Optional[int] = None) -> None:
        """Handle a rate limit response from the API."""
        current_time = time.time()
        self.consecutive_rate_limits += 1
        self.last_rate_limit_time = current_time
        
        # Calculate cooldown period
        base_cooldown = retry_after or (30 * self.consecutive_rate_limits)
        cooldown_time = base_cooldown * self.cooldown_factor
        
        self.is_cooling_down = True
        self.cooldown_until = current_time + cooldown_time
        
        # Reduce request rate temporarily
        self.requests_per_second = max(1.0, self.requests_per_second * 0.5)
        
        logger.warning(
            f"Rate limited! Cooling down for {cooldown_time:.2f}s. "
            f"Reduced rate to {self.requests_per_second:.1f} req/s"
        )
        
    def handle_success(self) -> None:
        """Handle a successful request."""
        if self.consecutive_rate_limits > 0:
            # Gradually increase rate after successful requests
            self.requests_per_second = min(
                10.0, self.requests_per_second * 1.1
            )
            
        self.consecutive_rate_limits = max(0, self.consecutive_rate_limits - 1)
        
        # Reset cooldown if we haven't been rate limited recently
        if time.time() - self.last_rate_limit_time > 300:  # 5 minutes
            self.is_cooling_down = False
            self.consecutive_rate_limits = 0


def adaptive_retry(
    max_retries: int = 5,
    backoff: Optional[ExponentialBackoff] = None,
    rate_limiter: Optional[RateLimiter] = None
):
    """
    Decorator for adaptive retry logic with rate limiting support.
    """
    if backoff is None:
        backoff = ExponentialBackoff()
        
    if rate_limiter is None:
        rate_limiter = RateLimiter()
        
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    # Wait for rate limiter permission
                    await rate_limiter.acquire()
                    
                    # Call the function
                    result = func(*args, **kwargs)
                    if asyncio.iscoroutine(result):
                        result = await result
                        
                    # Success! Update rate limiter
                    rate_limiter.handle_success()
                    return result
                    
                except requests.HTTPError as e:
                    last_exception = e
                    
                    if e.response.status_code == 429:
                        # Rate limited
                        retry_after = None
                        if 'Retry-After' in e.response.headers:
                            try:
                                retry_after = int(e.response.headers['Retry-After'])
                            except ValueError:
                                pass
                                
                        rate_limiter.handle_rate_limit(retry_after)
                        
                        if attempt < max_retries:
                            delay = backoff.calculate_delay(attempt, retry_after)
                            logger.warning(
                                f"Rate limited (attempt {attempt + 1}/{max_retries + 1}). "
                                f"Waiting {delay:.2f}s before retry..."
                            )
                            await asyncio.sleep(delay)
                            continue
                    elif e.response.status_code in [500, 502, 503, 504]:
                        # Server errors - retry with backoff
                        if attempt < max_retries:
                            delay = backoff.calculate_delay(attempt)
                            logger.warning(
                                f"Server error {e.response.status_code} "
                                f"(attempt {attempt + 1}/{max_retries + 1}). "
                                f"Retrying in {delay:.2f}s..."
                            )
                            await asyncio.sleep(delay)
                            continue
                    
                    # Don't retry for client errors (4xx except 429)
                    raise e
                    
                except (requests.RequestException, ConnectionError) as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        delay = backoff.calculate_delay(attempt)
                        logger.warning(
                            f"Connection error (attempt {attempt + 1}/{max_retries + 1}). "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                        continue
                        
                except Exception as e:
                    # Don't retry for other exceptions
                    raise e
                    
            # All retries exhausted
            raise last_exception or Exception("Max retries exceeded")
            
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # For sync functions, run in event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            return loop.run_until_complete(async_wrapper(*args, **kwargs))
            
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


class BatchProcessor:
    """
    Process requests in batches to avoid overwhelming the API.
    """
    
    def __init__(
        self,
        batch_size: int = 20,
        batch_delay: float = 2.0,
        rate_limiter: Optional[RateLimiter] = None
    ):
        self.batch_size = batch_size
        self.batch_delay = batch_delay
        self.rate_limiter = rate_limiter or RateLimiter()
        
    async def process_batch(
        self,
        items: list[Any],
        processor_func: Callable[[Any], Any],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> list[Any]:
        """
        Process items in batches with rate limiting and progress reporting.
        """
        results = []
        total_items = len(items)
        
        for i in range(0, total_items, self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_results = []
            
            logger.info(
                f"Processing batch {i//self.batch_size + 1}/{(total_items + self.batch_size - 1)//self.batch_size} "
                f"({len(batch)} items)"
            )
            
            # Process each item in the batch
            for j, item in enumerate(batch):
                try:
                    await self.rate_limiter.acquire()
                    result = processor_func(item)
                    if asyncio.iscoroutine(result):
                        result = await result
                    batch_results.append(result)
                    
                    if progress_callback:
                        progress_callback(i + j + 1, total_items)
                        
                except Exception as e:
                    logger.error(f"Failed to process item {item}: {e}")
                    batch_results.append(None)
                    
            results.extend(batch_results)
            
            # Wait between batches (except for the last one)
            if i + self.batch_size < total_items:
                logger.debug(f"Waiting {self.batch_delay}s between batches...")
                await asyncio.sleep(self.batch_delay)
                
        return results


# Global instances for convenience
default_rate_limiter = RateLimiter()
default_backoff = ExponentialBackoff()

def batch_processor(
    items: list[Any],
    processor_func: Callable[[Any], Any],
    batch_size: int = 20,
    batch_delay: float = 2.0,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> list[Any]:
    """
    Convenience function for batch processing.
    """
    processor = BatchProcessor(batch_size, batch_delay, default_rate_limiter)
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    return loop.run_until_complete(
        processor.process_batch(items, processor_func, progress_callback)
    )