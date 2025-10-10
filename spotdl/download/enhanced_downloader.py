"""
Enhanced downloader with intelligent batch processing and rate limiting.
This module provides improved download coordination to avoid overwhelming APIs.
"""

import asyncio
import logging
from typing import List, Optional, Tuple, Callable
from pathlib import Path

from spotdl.types.song import Song
from spotdl.download.downloader import Downloader as BaseDownloader
from spotdl.utils.rate_limiter import BatchProcessor, RateLimiter

__all__ = [
    "EnhancedDownloader",
    "SmartBatchConfig"
]

logger = logging.getLogger(__name__)


class SmartBatchConfig:
    """Configuration for intelligent batch processing."""
    
    def __init__(
        self,
        initial_batch_size: int = 15,
        min_batch_size: int = 5,
        max_batch_size: int = 50,
        adapt_on_errors: bool = True,
        error_threshold: float = 0.3,  # 30% error rate triggers adaptation
        batch_delay: float = 3.0,
        inter_song_delay: float = 0.5
    ):
        self.initial_batch_size = initial_batch_size
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.adapt_on_errors = adapt_on_errors
        self.error_threshold = error_threshold
        self.batch_delay = batch_delay
        self.inter_song_delay = inter_song_delay
        
        # Runtime state
        self.current_batch_size = initial_batch_size
        self.success_count = 0
        self.error_count = 0
        self.consecutive_successes = 0
        self.consecutive_errors = 0


class EnhancedDownloader(BaseDownloader):
    """
    Enhanced downloader with intelligent batch processing and adaptive rate limiting.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize batch configuration
        self.batch_config = SmartBatchConfig()
        
        # Enhanced rate limiting for different operations
        self.metadata_limiter = RateLimiter(
            requests_per_second=8.0,
            burst_limit=30,
            cooldown_factor=0.6
        )
        
        self.download_limiter = RateLimiter(
            requests_per_second=5.0,
            burst_limit=20,
            cooldown_factor=0.8
        )
        
        logger.info("Enhanced downloader initialized with adaptive batch processing")
        
    def download_multiple_songs_enhanced(
        self, 
        songs: List[Song],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Tuple[Song, Optional[Path]]]:
        """
        Download multiple songs using intelligent batch processing.
        
        ### Arguments
        - songs: The songs to download
        - progress_callback: Optional callback for progress updates (current, total, status)
        
        ### Returns
        - List of tuples with song and download path
        """
        total_songs = len(songs)
        
        if total_songs == 0:
            return []
            
        logger.info(f"Starting enhanced download of {total_songs} songs")
        
        # Pre-filter songs (archived, existing files, etc.)
        songs = self._pre_filter_songs(songs)
        filtered_count = len(songs)
        
        if filtered_count != total_songs:
            logger.info(f"Filtered to {filtered_count} songs (skipped {total_songs - filtered_count})")
        
        if filtered_count == 0:
            logger.info("No songs to download after filtering")
            return [(song, None) for song in songs]
            
        # Process songs in smart batches
        return asyncio.run(self._process_songs_in_batches(
            songs, progress_callback
        ))
        
    def _pre_filter_songs(self, songs: List[Song]) -> List[Song]:
        """Filter out songs that don't need to be downloaded."""
        if not songs:
            return []
            
        # Use existing filtering logic from parent class
        if self.settings["archive"]:
            songs = [song for song in songs if song.url not in self.url_archive]
            
        return songs
        
    async def _process_songs_in_batches(
        self,
        songs: List[Song],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Tuple[Song, Optional[Path]]]:
        """Process songs in intelligent batches."""
        results = []
        total_songs = len(songs)
        processed_count = 0
        
        # Split songs into batches
        batches = self._create_smart_batches(songs)
        
        logger.info(f"Processing {len(batches)} batches")
        
        for batch_idx, batch in enumerate(batches):
            batch_size = len(batch)
            
            if progress_callback:
                progress_callback(
                    processed_count, 
                    total_songs,
                    f"Processing batch {batch_idx + 1}/{len(batches)} ({batch_size} songs)"
                )
            
            logger.info(
                f"Processing batch {batch_idx + 1}/{len(batches)} "
                f"({batch_size} songs, current batch size: {self.batch_config.current_batch_size})"
            )
            
            # Process batch with rate limiting
            batch_results = await self._process_batch_with_rate_limiting(
                batch, processed_count, total_songs, progress_callback
            )
            
            results.extend(batch_results)
            processed_count += batch_size
            
            # Analyze batch results and adapt
            self._analyze_batch_results(batch_results)
            
            # Wait between batches (except for the last one)
            if batch_idx < len(batches) - 1:
                logger.debug(f"Waiting {self.batch_config.batch_delay}s between batches")
                await asyncio.sleep(self.batch_config.batch_delay)
                
        logger.info(f"Enhanced download completed: {len(results)} songs processed")
        return results
        
    def _create_smart_batches(self, songs: List[Song]) -> List[List[Song]]:
        """Create intelligently sized batches based on current performance."""
        batches = []
        current_batch_size = self.batch_config.current_batch_size
        
        for i in range(0, len(songs), current_batch_size):
            batch = songs[i:i + current_batch_size]
            batches.append(batch)
            
        return batches
        
    async def _process_batch_with_rate_limiting(
        self,
        batch: List[Song],
        start_index: int,
        total_songs: int,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Tuple[Song, Optional[Path]]]:
        """Process a batch of songs with proper rate limiting."""
        batch_results = []
        
        # Create semaphore for concurrent processing within batch
        # Limit concurrency to avoid overwhelming the system
        max_concurrent = min(self.settings["threads"], len(batch), 8)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_song(song: Song, song_index: int) -> Tuple[Song, Optional[Path]]:
            async with semaphore:
                # Rate limiting for metadata requests
                await self.metadata_limiter.acquire()
                
                try:
                    # Use parent class method for actual download
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self.search_and_download, song
                    )
                    
                    if progress_callback:
                        progress_callback(
                            start_index + song_index + 1,
                            total_songs,
                            f"Downloaded: {song.display_name}"
                        )
                        
                    # Brief pause between downloads in the same batch
                    if song_index < len(batch) - 1:
                        await asyncio.sleep(self.batch_config.inter_song_delay)
                        
                    return result
                    
                except Exception as e:
                    logger.error(f"Failed to download {song.display_name}: {e}")
                    
                    if progress_callback:
                        progress_callback(
                            start_index + song_index + 1,
                            total_songs,
                            f"Failed: {song.display_name}"
                        )
                        
                    return song, None
        
        # Process all songs in the batch concurrently
        tasks = [
            process_single_song(song, idx) 
            for idx, song in enumerate(batch)
        ]
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions that occurred
        final_results = []
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.error(f"Task exception for song {batch[i].display_name}: {result}")
                final_results.append((batch[i], None))
            else:
                final_results.append(result)
                
        return final_results
        
    def _analyze_batch_results(self, batch_results: List[Tuple[Song, Optional[Path]]]) -> None:
        """Analyze batch results and adapt batch size accordingly."""
        if not self.batch_config.adapt_on_errors:
            return
            
        # Count successes and failures
        batch_successes = sum(1 for _, path in batch_results if path is not None)
        batch_failures = len(batch_results) - batch_successes
        batch_error_rate = batch_failures / len(batch_results) if batch_results else 0
        
        # Update global counters
        self.batch_config.success_count += batch_successes
        self.batch_config.error_count += batch_failures
        
        # Track consecutive results
        if batch_error_rate > self.batch_config.error_threshold:
            self.batch_config.consecutive_errors += 1
            self.batch_config.consecutive_successes = 0
        else:
            self.batch_config.consecutive_successes += 1
            self.batch_config.consecutive_errors = 0
            
        # Adapt batch size based on performance
        if self.batch_config.consecutive_errors >= 2:
            # Reduce batch size after consecutive errors
            new_size = max(
                self.batch_config.min_batch_size,
                int(self.batch_config.current_batch_size * 0.7)
            )
            if new_size != self.batch_config.current_batch_size:
                logger.warning(
                    f"Reducing batch size from {self.batch_config.current_batch_size} "
                    f"to {new_size} due to errors"
                )
                self.batch_config.current_batch_size = new_size
                
        elif self.batch_config.consecutive_successes >= 3:
            # Increase batch size after consecutive successes
            new_size = min(
                self.batch_config.max_batch_size,
                int(self.batch_config.current_batch_size * 1.2)
            )
            if new_size != self.batch_config.current_batch_size:
                logger.info(
                    f"Increasing batch size from {self.batch_config.current_batch_size} "
                    f"to {new_size} due to good performance"
                )
                self.batch_config.current_batch_size = new_size
                
        # Log current statistics
        total_processed = self.batch_config.success_count + self.batch_config.error_count
        overall_success_rate = (
            self.batch_config.success_count / total_processed 
            if total_processed > 0 else 0
        )
        
        logger.debug(
            f"Batch completed: {batch_successes}/{len(batch_results)} successful. "
            f"Overall: {self.batch_config.success_count}/{total_processed} "
            f"({overall_success_rate:.1%} success rate)"
        )
        
    def get_download_stats(self) -> dict:
        """Get current download statistics."""
        total = self.batch_config.success_count + self.batch_config.error_count
        return {
            "total_processed": total,
            "successful": self.batch_config.success_count,
            "failed": self.batch_config.error_count,
            "success_rate": self.batch_config.success_count / total if total > 0 else 0,
            "current_batch_size": self.batch_config.current_batch_size,
            "consecutive_successes": self.batch_config.consecutive_successes,
            "consecutive_errors": self.batch_config.consecutive_errors
        }