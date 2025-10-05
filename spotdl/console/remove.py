"""
Remove module for the console.

This module provides functionality to remove songs that were downloaded from a Spotify playlist.
It matches files based on the same naming pattern used during download.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from spotdl.types.song import Song
from spotdl.utils.spotify import SpotifyClient
from spotdl.utils.search import get_simple_songs

__all__ = ["remove"]

logger = logging.getLogger(__name__)

def remove(
    query: List[str],
    downloader: Any = None,  # Keep for backward compatibility
    output: str = "{artists} - {title}.{output-ext}",
    audio_format: str = "mp3",
) -> None:
    """
    Remove songs from the local directory that match the given Spotify playlist URL.

    ### Arguments
    - query: List of Spotify playlist URLs to remove songs from.
    - output: Output format for the song file.
    - audio_format: Audio format to look for when removing files.

    ### Example
    ```
    python -m spotdl remove "https://open.spotify.com/playlist/..." \
        --output "{artist} - {title}.{output-ext}" \
        --format "mp3"
    ```
    """
    # Initialize spotify client to get playlist data
    spotify_client = SpotifyClient()
    
    if not query:
        logger.error("No playlist URL provided")
        return
        
    logger.info(f"Fetching songs from {len(query)} playlist(s)...")
    
    # Get all songs from the playlist
    songs = get_simple_songs(
        query,
        use_ytm_data=False,
        playlist_numbering=False,
        albums_to_ignore=[],
        album_type=None,
        playlist_retain_track_cover=False,
    )
    
    if not songs:
        logger.warning("No songs found in the provided playlist URL")
        return
    
    logger.info(f"Found {len(songs)} songs in the playlist")
    
    # Convert output format to match the file naming pattern
    output = output.replace("{output-ext}", audio_format)
    
    # Get the base directory from the output format
    output_dir = os.path.dirname(output)
    if not output_dir:
        output_dir = "."
    
    logger.info(f"Searching for matching files in: {os.path.abspath(output_dir)}")
    
    # Get all files in the output directory
    all_files = []
    for root, _, files in os.walk(output_dir):
        for file in files:
            if file.lower().endswith(f".{audio_format.lower()}"):
                all_files.append(Path(root) / file)
    
    if not all_files:
        logger.warning(f"No {audio_format} files found in the output directory")
        return
    
    logger.info(f"Found {len(all_files)} {audio_format} files to check")
    
    # Track removed files
    removed_count = 0
    removed_files = []
    
    for song in songs:
        # Generate the expected filename for this song
        try:
            formatted_output = output.format(
                title=song.name or "Unknown",
                artists=", ".join(song.artists) if song.artists else "Unknown",
                artist=song.artists[0] if song.artists else "Unknown",
                album=song.album_name if song.album_name else "Unknown",
                album_artist=song.album_artist if song.album_artist else "Unknown",
                date=song.date if song.date else "Unknown",
                year=song.year if song.year else "Unknown",
                track_number=str(song.track_number).zfill(2) if song.track_number else "01",
                tracks_in_album=str(song.tracks_count).zfill(2) if song.tracks_count else "01",
                disc_number=str(song.disc_number).zfill(2) if song.disc_number else "01",
                discs_in_album=str(song.disc_count).zfill(2) if song.disc_count else "01",
                isrc=song.song_id if song.song_id else "Unknown",
                output_ext=audio_format,
            )
            expected_filename = Path(formatted_output).resolve()
        except (KeyError, IndexError) as e:
            logger.warning(f"Error formatting output for song {song.name}: {str(e)}")
            continue
        
        # Look for files that match the expected pattern
        for file_path in all_files[:]:  # Make a copy of the list to modify it while iterating
            try:
                if file_path.name.lower() == expected_filename.name.lower():
                    try:
                        file_path.unlink()
                        logger.debug(f"Removed: {file_path}")
                        removed_files.append(str(file_path))
                        all_files.remove(file_path)  # Remove from list to avoid double processing
                        removed_count += 1
                    except OSError as e:
                        logger.error(f"Error removing {file_path}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Unexpected error removing {file_path}: {str(e)}")
                        raise
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
    
    # Print summary
    if removed_count > 0:
        logger.info("\nRemoved the following files:")
        for file_path in removed_files:
            logger.info(f"- {file_path}")
        
        logger.info(f"\nSuccessfully removed {removed_count} files from the playlist.")
    else:
        logger.warning("\nNo matching files found to remove.")
    
    # If we didn't find any files to remove, show a helpful message
    if removed_count == 0:
        logger.warning("\nThe files may have already been removed or the naming format doesn't match.")
        logger.info("\nTip: Make sure the output format matches the one used when downloading the files.")
        logger.info(f"Example format used: {output}")
        
        if songs:
            example_song = songs[0]
            try:
                example_output = output.format(
                    title=example_song.name or "Example Title",
                    artists="Example Artist",
                    artist="Example Artist",
                    album=example_song.album_name or "Example Album",
                    album_artist=example_song.album_artist or "Example Artist",
                    date=example_song.date or "2023",
                    year=example_song.year or "2023",
                    track_number="01",
                    tracks_in_album="12",
                    disc_number="01",
                    discs_in_album="01",
                    isrc="EXAMPLE123",
                    output_ext=audio_format,
                )
                logger.info(f"Example output: {example_output}")
            except Exception as e:
                logger.debug(f"Could not generate example output: {str(e)}")
