#!/usr/bin/env python3
"""
SpotDL Web Interface
Custom web UI that replaces the original SpotDL web interface with        return await track_real_progress() layout and functionality requirements.
"""

import asyncio
import json
import os
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import multiprocessing
import queue
import concurrent.futures
import tkinter as tk
from tkinter import filedialog
import socket

# FastAPI imports
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request,HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# SpotDL imports - using browser auth from simple_spotdl.py
import subprocess

def find_available_port(start_port: int = 8807, max_attempts: int = 10) -> int:
    """
    Find an available port starting from start_port.
    Tries up to max_attempts ports sequentially.
    Robustness with more port attempts and better error handling.
    """
    for attempt in range(max_attempts):
        port = start_port + attempt
        try:
            # Test if port is available by attempting to bind
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('localhost', port))
                return port
        except (OSError, Exception):
            continue
    
    # If no port found, provide helpful error message
    port_range = f"{start_port}-{start_port + max_attempts - 1}"
    raise RuntimeError(
        f"Could not find an available port after {max_attempts} attempts in range {port_range}. "
        f"Please close any applications using ports in this range and try again, or restart your system."
    )

def get_spotify_browser_auth(force_refresh=False):
    """Get Spotify authentication using browser auth (cached with error handling)"""
    global _cached_spotify_auth
    
    # Return cached auth if available and validate it has access_token (unless force refresh)
    if _cached_spotify_auth is not None and not force_refresh:
        if hasattr(_cached_spotify_auth, 'access_token') and _cached_spotify_auth.access_token:
            return _cached_spotify_auth
        else:
            _cached_spotify_auth = None
    
    try:
        from spotdl.utils.browser_auth import BrowserSpotifyAuth
        import sys
        import os
        
        print("Authenticating with Spotify...")
        
        # Suppress stderr during auth
        original_stderr = sys.stderr
        try:
            sys.stderr = open(os.devnull, 'w')
            _cached_spotify_auth = BrowserSpotifyAuth.authorize()
        finally:
            sys.stderr.close()
            sys.stderr = original_stderr
            
        # Validate the auth result
        if _cached_spotify_auth and hasattr(_cached_spotify_auth, 'access_token') and _cached_spotify_auth.access_token:
            print("Authentication successful!")
        else:
            _cached_spotify_auth = None
            
        return _cached_spotify_auth
    except Exception as e:
        logger.error(f"Browser auth failed: {e}")
        _cached_spotify_auth = None
        return None

def download_with_progress_queue(url: str, output_dir: str, progress_queue, songs_data, skipped_songs_set, auth_token: str = None):
    """Download function that runs in separate process and sends progress via queue"""

    
    try:
        # Import here to avoid issues with multiprocessing
        import sys
        import os
        import tempfile
        import json
        import time
        import signal
        
        # Track songs that have already been marked as "exists" to prevent duplicate "success" messages
        already_exists_songs = set()
        
        # Set up signal handler for immediate termination
        def terminate_handler(signum, frame):
            print("Download process terminated immediately!")
            sys.exit(1)
        
        signal.signal(signal.SIGTERM, terminate_handler)
        signal.signal(signal.SIGINT, terminate_handler)
        
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from simple_spotdl import download_playlist
        
        # Create a temporary file to store skipped songs that the download process can check
        skipped_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json')
        skipped_file_path = skipped_file.name
        skipped_file.close()
        
        # Function to update skipped songs file with current shared list
        def update_skipped_file():
            try:
                with open(skipped_file_path, 'w') as f:
                    # Get current list from shared memory
                    current_skipped = list(skipped_songs_set) if skipped_songs_set else []
                    json.dump(current_skipped, f)
            except:
                pass
        
        # Initial write
        update_skipped_file()
        
        # Override print to capture progress
        original_print = print
        current_song_index = 0
        processed_songs = set()  # Track processed songs to avoid duplicates
        existing_songs = set()  # Track which songs already exist
        
        def progress_print(*args, **kwargs):
            line = " ".join(str(arg) for arg in args)
            
            try:
                # Update the skipped songs file periodically
                update_skipped_file()
                
                # Skip processing our own WebSocket logging messages to avoid feedback loop
                if line.startswith("WebSocket"):
                    original_print(*args, **kwargs)
                    return
                
                # Check for "Already exists" messages first
                if "⏭Already exists:" in line:
                    try:
                        # Parse format: "⏭Already exists: Song Name by Artist"
                        import re
                        match = re.search(r"⏭Already exists: (.+?) by (.+?)$", line)
                        if match:
                            song_name_exists, artist_exists = match.groups()
                            existing_songs.add(song_name_exists.strip())
                    except Exception as e:
                        pass
                
                # Intercept send_web_progress calls and put them directly in the progress queue
                # This bypasses the global variable issue in multiprocessing
                if line.startswith("Song "):
                    try:
                        # Parse format: "Song 1/50: Song Name → status (percentage%)"
                        import re
                        match = re.search(r"Song (\d+)/(\d+): (.+?) → (\w+)", line)
                        if match:
                            current_idx, total_songs, song_name, status = match.groups()
                            
                            # Find matching song data to get song_id
                            song_id = f"song_{current_idx}"
                            artist = "Unknown Artist"
                            
                            # Try to find the song in our songs_data
                            for song in songs_data:
                                if song.get('name', '').lower().strip() in song_name.lower() or song_name.lower().strip() in song.get('name', '').lower():
                                    song_id = song.get('song_id', song_id)
                                    artist = song.get('artist', artist)
                                    break
                            
                            # Check if this song was marked as already existing
                            song_already_exists = any(existing_name in song_name for existing_name in existing_songs)
                            
                            # For existing files that show as "success", treat them as "exists"
                            if song_already_exists and status == "success":
                                # First send downloading status for animation
                                progress_data_downloading = {
                                    "song_id": song_id,
                                    "song_name": song_name,
                                    "artist": artist,
                                    "status": "downloading",
                                    "progress": 10,
                                    "current_index": int(current_idx),
                                    "total_songs": int(total_songs),
                                    "message": "Checking file...",
                                    "timestamp": time.time()
                                }
                                progress_queue.put_nowait(progress_data_downloading)
                                # Suppressed: print(f"WebSocket {current_idx}/{total_songs}: {song_name} → downloading")
                                
                                # Brief delay then send exists status
                                time.sleep(0.1)
                                
                                progress_data_exists = {
                                    "song_id": song_id,
                                    "song_name": song_name,
                                    "artist": artist,
                                    "status": "exists",
                                    "progress": 100,
                                    "current_index": int(current_idx),
                                    "total_songs": int(total_songs),
                                    "message": "Already downloaded",
                                    "timestamp": time.time()
                                }
                                progress_queue.put_nowait(progress_data_exists)
                                
                                # Track this song as already exists to prevent duplicate "success" messages
                                already_exists_songs.add(song_name.lower().strip())
                                # Suppressed: print(f"WebSocket {current_idx}/{total_songs}: {song_name} → exists")
                            else:
                                # For genuinely new downloads, send as-is
                                frontend_status = "success" if status == "success" else status
                                progress_value = 10 if frontend_status == "downloading" else (100 if frontend_status == "success" else 0)
                                
                                progress_data = {
                                    "song_id": song_id,
                                    "song_name": song_name,
                                    "artist": artist,
                                    "status": frontend_status,
                                    "progress": progress_value,
                                    "current_index": int(current_idx),
                                    "total_songs": int(total_songs),
                                    "message": f"{'Downloading...' if frontend_status == 'downloading' else 'Completed'}",
                                    "timestamp": time.time()
                                }
                                
                                progress_queue.put_nowait(progress_data)
                                # Suppressed: print(f"WebSocket {current_idx}/{total_songs}: {song_name} → {frontend_status}")
                            
                    except Exception as e:
                        print(f"Error processing progress line: {e}")
                        pass
                
                # Parse clean terminal output instead of WEBUI_DATA
                web_data = None
                
                # Parse "Already exists" messages for tracking
                if "Already exists:" in line:
                    # Parse format: "Already exists: Song Name by Artist"
                    try:
                        import re
                        match = re.search(r"Already exists: (.+?) by (.+)", line)
                        if match:
                            song_title = match.group(1).strip()
                            artist = match.group(2).strip()
                            song_name = f"{song_title}"  # Just the title for matching
                            
                            # Track this song as already exists - don't create web_data yet
                            # Wait for the numbered message which will have proper index/total
                            already_exists_songs.add(song_name.lower().strip())
                    except:
                        pass
                
                # Parse main progress messages
                elif line.startswith("📤 Song "):
                    # Parse format: "📤 Song 1/24: Song Name → status (percentage%)"
                    try:
                        import re
                        match = re.match(r"📤 Song (\d+)/(\d+): (.+?) → (\w+) \((\d+)%\)", line)
                        if match:
                            current_index = int(match.group(1))
                            total_songs = int(match.group(2))
                            song_name = match.group(3)
                            status = match.group(4)
                            percentage = int(match.group(5))
                            
                            # Check if this song was marked as already existing
                            if song_name.lower().strip() in already_exists_songs and status == "success":
                                # Convert to "exists" status since this file already existed
                                status = "exists"
                                message = "Already downloaded"
                            else:
                                # Handle different status types properly
                                if status == "success" and percentage == 100:
                                    # This is an actual successful download
                                    status = "success"
                                    message = "Download completed"
                                elif status == "downloading":
                                    message = "Downloading..."
                                elif status == "processing":
                                    message = "Processing..."
                                else:
                                    message = f"{status.capitalize()}" + (" completed" if status == "success" else "")
                            
                            # Create web_data format from parsed terminal output
                                web_data = {
                                    "song_name": song_name,
                                    "status": status,
                                    "current_index": current_index,
                                    "total_songs": total_songs,
                                    "message": message
                                }
                    except:
                        pass
                        
                # Only process if we found valid web_data
                if web_data:
                    # Create a unique key for deduplication
                    song_key = f"{web_data['song_name']}_{web_data.get('current_index', 0)}"
                    
                    # Track existing files to distinguish from actual downloads
                    if web_data['status'] == 'exists':
                        # This is from "Already exists" message - mark as existing
                        processed_songs.add(f"exists_{song_key}")
                    elif web_data['status'] == 'success' and f"exists_{song_key}" in processed_songs:
                        # This success message is for a file that already exists - convert to exists status
                        web_data['status'] = 'exists'
                        web_data['message'] = 'Already downloaded'
                    
                    # Add to processed set
                    processed_songs.add(song_key)
                        
                    # Find matching song in songs_data for song_id with fuzzy matching
                    song_id = None
                    download_name = web_data["song_name"].lower().strip()
                    
                    # First try: Use current_index to directly map to song if available and valid
                    if web_data.get("current_index", 0) > 0 and len(songs_data) >= web_data["current_index"]:
                        try:
                            # current_index is 1-based, so subtract 1 for 0-based array access
                            direct_song = songs_data[web_data["current_index"] - 1]
                            song_id = direct_song["song_id"]
                            print(f"Debug: Direct index match for {download_name} -> {song_id}")
                        except (IndexError, KeyError):
                            pass  # Fall back to fuzzy matching
                    
                    # Initialize variables before fuzzy matching
                    download_artist = ""
                    download_song_only = download_name
                    
                    # If direct index matching failed, try fuzzy matching
                    if not song_id:
                        # Extract artist from song name if it follows "Artist - Song" format
                        if " - " in download_name:
                            parts = download_name.split(" - ", 1)
                            download_artist = parts[0].strip()
                            download_song_only = parts[1].strip()
                        else:
                            download_artist = ""
                            download_song_only = download_name
                    
                    # Try multiple matching strategies
                    for song in songs_data:
                        frontend_name = song["name"].lower().strip()
                        frontend_artist = song["artist"].lower().strip()
                        
                        # Strategy 1: Exact match
                        if frontend_name == download_song_only and frontend_artist == download_artist:
                            song_id = song["song_id"]
                            break
                            
                        # Strategy 2: Check if download name contains song title
                        if frontend_name in download_name and frontend_artist in download_name:
                            song_id = song["song_id"]
                            break
                            
                        # Strategy 3: Check if song title is in download name (for "Artist - Song" format)
                        if frontend_name in download_name and any(artist.lower().strip() in download_name for artist in frontend_artist.split(", ")):
                            song_id = song["song_id"]
                            break
                            
                        # Strategy 4: Partial title match (for different formatting)
                        name_words = set(frontend_name.replace("-", " ").split())
                        download_words = set(download_name.replace("-", " ").split())
                        if len(name_words.intersection(download_words)) >= min(2, len(name_words)):
                            artist_words = set(frontend_artist.replace(",", " ").split())
                            if len(artist_words.intersection(download_words)) >= 1:
                                song_id = song["song_id"]
                                break
                    
                    # Check if this song should be skipped
                    if song_id and song_id in skipped_songs_set:
                        # Song was cancelled, skip silently
                        progress_queue.put({
                            "song_id": song_id,
                            "song_name": web_data["song_name"],
                            "artist": download_artist,
                            "progress": 0,
                            "status": "cancelled",
                            "message": "Skipped by user",
                            "current_index": web_data["current_index"],
                            "total_songs": web_data["total_songs"]
                        })
                        return  # Don't send the original progress update
                    
                    # Debug logging (suppress for clean terminal)
                    # Matching debug info removed for clean output
                    
                    # Set progress based on status (frontend will handle the animation)
                    individual_progress = 0
                    if web_data["status"] in ["success", "exists", "completed"]:
                        individual_progress = 100  # Completed - frontend will jump to 100%
                    elif web_data["status"] in ["downloading", "processing"]:
                        individual_progress = 1    # Started - frontend will begin animation
                    elif web_data["status"] == "error":
                        individual_progress = 0    # Error - no progress
                    
                    # If we still don't have a song_id, try one more approach using position-based matching
                    if not song_id and web_data.get("current_index", 0) > 0:
                        # Try to find song by position in the original order
                        try:
                            position_song = songs_data[web_data["current_index"] - 1]
                            # Simple name similarity check
                            frontend_name = position_song["name"].lower().replace(" ", "").replace("-", "")
                            download_name_clean = download_name.replace(" ", "").replace("-", "")
                            if frontend_name in download_name_clean or download_name_clean in frontend_name:
                                song_id = position_song["song_id"]
                                print(f"Debug: Position-based match for {download_name} -> {song_id}")
                        except (IndexError, KeyError):
                            pass
                    
                    # Send progress update with immediate processing for skipped songs
                    progress_data = {
                        "song_id": song_id or f"unknown-{web_data.get('current_index', 0)}",
                        "song_name": web_data["song_name"],
                        "artist": download_artist if 'download_artist' in locals() else "",
                        "progress": individual_progress,
                        "status": web_data["status"],
                        "message": web_data["message"],
                        "current_index": web_data["current_index"],
                        "total_songs": web_data["total_songs"]
                    }
                    
                    # For existing/skipped songs, add priority flag to ensure they're processed quickly
                    if web_data["status"] == "exists":
                        progress_data["priority"] = True
                        
                    progress_queue.put(progress_data)
                        
            except Exception as e:
                print(f"Error in progress parsing: {e}")
            
            # Call original print
            original_print(*args, **kwargs)
        
        # Replace print temporarily
        import builtins
        builtins.print = progress_print
        
        try:
            # Use the auth token passed from parent process (no need to get it again)
            if not auth_token:
                logger.warning("No authentication token provided to subprocess")
            
            result = download_playlist(url, output_dir, web_mode=True, auth_token=auth_token)
            return result
        finally:
            builtins.print = original_print
            
            # Clean up the temporary skipped songs file
            try:
                os.unlink(skipped_file_path)
            except:
                pass
            
    except Exception as e:
        print(f"Download process error: {e}")
        return False

async def download_playlist_progress(url, progress_callback, client_id):
    """Download with real progress tracking using multiprocessing"""
    try:
        import sys
        import os
        import time
        import subprocess
        
        # Add the current directory to path to import simple_spotdl
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import the download function
        from simple_spotdl import download_playlist
        
        # Run the actual download in a thread to avoid blocking
        import concurrent.futures
        import threading
        
        downloaded_count = 0
        total_songs = 0
        
        # Get the songs data we already fetched for progress tracking
        client_id = None
        for cid in client_urls:
            if client_urls[cid] == url:
                client_id = cid
                break
        
        if client_id and client_id in playlist_info:
            total_songs = playlist_info[client_id].get("total_tracks", 0)
        
        # Track real progress with actual song data
        async def track_real_progress():
            nonlocal downloaded_count
            
            # Get the real songs from stored data
            songs_data = []
            if client_id and client_id in client_songs:
                # Use the real songs data stored from the API call
                songs_data = client_songs[client_id]
                print(f"Found {len(songs_data)} songs for progress tracking")
            
            # Start the actual download in background
            def run_download():
                try:
                    output_dir = os.path.join(os.path.expanduser("~"), "Downloads", "SpotDL")
                    os.makedirs(output_dir, exist_ok=True)
                    # Get cached auth token to pass to download process
                    spotify_auth = get_spotify_browser_auth()
                    auth_token = spotify_auth.access_token if spotify_auth else None
                    return download_playlist(url, output_dir, web_mode=True, auth_token=auth_token)
                except Exception as e:
                    print(f"Download error: {e}")
                    return False
            
            # Start download with real progress monitoring using direct function call
            # Import the download function
            from simple_spotdl import download_playlist
            
            # Create a shared state for progress monitoring
            current_song_info = {"index": 0, "status": "starting"}
            
            def run_download_with_progress():
                try:
                    output_dir = os.path.join(os.path.expanduser("~"), "Downloads", "SpotDL")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # Monkey patch print to capture download progress
                    original_print = print
                    
                    def progress_print(*args, **kwargs):
                        line = " ".join(str(arg) for arg in args)
                        
                        # Update shared state based on output
                        if "→ downloading" in line or "Downloading:" in line:
                            current_song_info["status"] = "downloading"
                        elif ("✅" in line and ("done" in line.lower() or "completed" in line.lower())) or "→ success (100%)" in line:
                            current_song_info["status"] = "completed"
                            current_song_info["index"] += 1
                        elif "❌" in line or "failed" in line.lower():
                            current_song_info["status"] = "error"
                        
                        # Call original print
                        original_print(*args, **kwargs)
                    
                    # Temporarily replace print
                    import builtins
                    builtins.print = progress_print
                    
                    try:
                        # Get cached auth token to pass to download process
                        spotify_auth = get_spotify_browser_auth()
                        auth_token = spotify_auth.access_token if spotify_auth else None
                        result = download_playlist(url, output_dir, web_mode=True, auth_token=auth_token)
                        return result
                    finally:
                        # Restore original print
                        builtins.print = original_print
                        
                except Exception as e:
                    print(f"Download error: {e}")
                    return False
            
            # Start the download in a thread and monitor progress
            with concurrent.futures.ThreadPoolExecutor() as executor:
                download_future = executor.submit(run_download_with_progress)
                
                # Store the future for potential cancellation
                active_downloads[client_id] = download_future
                
                last_song_index = -1
                
                # Monitor progress every second
                while not download_future.done():
                    try:
                        # Check if song index changed
                        if current_song_info["index"] != last_song_index:
                            # New song or status change
                            if current_song_info["index"] < len(songs_data):
                                song = songs_data[current_song_info["index"]]
                                
                                if current_song_info["status"] == "downloading":
                                    await progress_callback(
                                        song["name"],
                                        song["artist"],
                                        50,  # Mid progress
                                        "Downloading...",
                                        song_id=song["song_id"]
                                    )
                                elif current_song_info["status"] == "completed":
                                    await progress_callback(
                                        song["name"],
                                        song["artist"],
                                        100,
                                        "completed",
                                        song_id=song["song_id"]
                                    )
                            
                            last_song_index = current_song_info["index"]
                        
                        await asyncio.sleep(1.0)  # Check every second
                        
                    except Exception as e:
                        print(f"Error monitoring download: {e}")
                        break
                
                # Wait for completion
                try:
                    result = download_future.result(timeout=5)
                except concurrent.futures.TimeoutError:
                    print("Download timed out")
                    result = False
                
                # Clean up
                if client_id in active_downloads:
                    del active_downloads[client_id]
                
                return result
            
            return False
        
        return await track_real_progress()
    
    except Exception as e:
        print(f"Error in download_playlist_progress: {e}")
        await progress_callback("Error", str(e), 0, "error")
        return False
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        # Fallback to simulation
        songs = [
            ("Room 5", "Make Luv"),
            ("nimino, Maverick Sabre", "Beside Of Me"), 
            ("Mike Posner", "I Took A Pill In Ibiza")
        ]
        
        for i, (artist, title) in enumerate(songs):
            for progress in [0.0, 0.5, 1.0]:
                await progress_callback(title, artist, progress, "downloading" if progress < 1.0 else "completed")
                await asyncio.sleep(0.8)
        
        return {"downloaded_count": len(songs)}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="SpotDL Web Interface", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
websocket_connections: Dict[str, WebSocket] = {}
client_urls: Dict[str, str] = {}
playlist_info: Dict[str, Dict] = {}
client_songs: Dict[str, List] = {}  # Store songs data for each client
active_downloads: Dict[str, any] = {}  # Store active download futures
shutdown_event = asyncio.Event()  # Global shutdown signal
progress_queues: Dict[str, any] = {}  # Store progress queues for each client
skipped_songs: Dict[str, any] = {}  # Store skipped song IDs for each client
_web_progress_data: List = []  # Clean progress data storage without WEBUI_DATA clutter

# Global authentication cache
_cached_spotify_auth = None



class DownloadRequest(BaseModel):
    url: str
    client_id: str
    output_path: Optional[str] = None

class URLRequest(BaseModel):
    url: str

# WebSocket connection manager
async def send_song_update(client_id: str, song_title: str, artist: str, progress: float, status: str, message: str = "", song_id: str = None):
    """Send real-time song progress updates via WebSocket"""
    if client_id in websocket_connections:
        try:
            # Use the provided song_id (should be the Spotify track ID)
            if not song_id:
                logger.warning(f"No song_id provided for {song_title} by {artist}")
                return
            
            websocket_message = {
                "song": {"song_id": song_id},
                "progress": progress / 100.0 if progress > 1 else progress,  # Ensure 0-1 scale
                "status": status,
                "message": message or status
            }
            
            # Suppressed: print(f"Sending WebSocket update: song_id={song_id}, progress={progress}%, status={status}")
            await websocket_connections[client_id].send_text(json.dumps(websocket_message))
            
        except Exception as e:
            logger.error(f"Error sending WebSocket update: {e}")

async def monitor_progress_queue(client_id: str):
    """Background task to monitor progress queue and send WebSocket updates"""
    if client_id not in progress_queues:
        print(f"No progress queue found for client {client_id}")
        return
    
    progress_queue = progress_queues[client_id]
    print(f"Starting progress monitoring for client {client_id}")
    
    try:
        consecutive_empty = 0
        while client_id in websocket_connections and client_id in progress_queues:
            try:
                # Process all available items in queue (especially rapid skipped songs)
                items_processed = 0
                while items_processed < 10:  # Process up to 10 items at once to catch up
                    try:
                        progress_data = progress_queue.get_nowait()
                        items_processed += 1
                        consecutive_empty = 0
                        
                        # Send update via WebSocket if connection exists
                        if client_id in websocket_connections:
                            websocket_message = {
                                "type": "progress_update",
                                "song": {"song_id": progress_data["song_id"]},
                                "progress": progress_data["progress"] / 100.0,  # Convert to 0-1 scale (0.0 to 1.0)
                                "status": progress_data["status"],
                                "message": progress_data.get("message", progress_data["status"]),
                                "current_song": progress_data.get("current_index", 0),
                                "total_songs": progress_data.get("total_songs", 0)
                            }
                            
                            try:
                                await websocket_connections[client_id].send_text(json.dumps(websocket_message))
                                
                                # For existing files, add a small delay to ensure UI catches up
                                if progress_data["status"] == "exists":
                                    await asyncio.sleep(0.05)  # 50ms delay for skipped songs to be visible
                                    
                            except Exception as ws_error:
                                # Suppressed: print(f"WebSocket send error for {client_id}: {ws_error}")
                                # Remove broken connection
                                if client_id in websocket_connections:
                                    del websocket_connections[client_id]
                                break
                        
                        # Log progress (minimal) - use different format to avoid feedback loop
                        if progress_data['status'] in ['success', 'error', 'exists']:
                            song_num = progress_data.get("current_index", "?")
                            total = progress_data.get("total_songs", "?")
                            status_emoji = "✅" if progress_data['status'] in ['success', 'exists'] else "❌"
                            status_text = "already downloaded" if progress_data['status'] == 'exists' else progress_data['status']
                            # Use different emoji to avoid parsing conflicts
                            print(f"� WebSocket {song_num}/{total}: {progress_data['song_name']} → {status_text}")
                        
                    except queue.Empty:
                        # No more items available
                        break
                        
                # If we didn't process any items, increment empty counter
                if items_processed == 0:
                    consecutive_empty += 1
                    
                # Adaptive sleep based on queue activity
                try:
                    if consecutive_empty < 3:
                        await asyncio.sleep(0.05)  # Fast polling when active
                    else:
                        await asyncio.sleep(0.1)   # Slower polling when idle
                except asyncio.CancelledError:
                    # Handle graceful shutdown
                    break
                    
            except Exception as e:
                logger.error(f"Error processing progress update: {e}")
                break
                
    except Exception as e:
        logger.error(f"Progress monitoring error for {client_id}: {e}")
    finally:
        # Clean up
        if client_id in progress_queues:
            del progress_queues[client_id]

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket connection for real-time updates"""
    await websocket.accept()
    websocket_connections[client_id] = websocket
    
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "client_id": client_id,
            "message": "WebSocket connection established"
        }))
        
        try:
            while True:
                # Keep connection alive and check if connection is still active
                try:
                    # Send a ping every few seconds to keep connection alive
                    await asyncio.sleep(2)
                    await websocket.send_text(json.dumps({
                        "type": "ping",
                        "timestamp": asyncio.get_event_loop().time()
                    }))
                except asyncio.CancelledError:
                    # Handle graceful shutdown
                    break
                except Exception as e:
                    # Suppressed: print(f"WebSocket connection lost for {client_id}: {e}")
                    break
        except asyncio.CancelledError:
            # Handle graceful shutdown during sleep
            pass
                
    except WebSocketDisconnect:
        # Suppressed: print(f"WebSocket disconnected for client {client_id}")
        pass
    except Exception as e:
        # Suppressed: print(f"WebSocket error for client {client_id}: {e}")
        pass
    finally:
        # Cleanup
        if client_id in websocket_connections:
            del websocket_connections[client_id]
        # Suppressed: print(f"WebSocket cleanup completed for client {client_id}")

@app.post("/api/refresh-auth")
async def refresh_authentication():
    """Force refresh Spotify authentication"""
    try:
        spotify_auth = get_spotify_browser_auth(force_refresh=True)
        if spotify_auth:
            return JSONResponse(content={
                "status": "success",
                "message": "Authentication refreshed successfully"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to refresh authentication")
    except Exception as e:
        logger.error(f"Auth refresh failed: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication refresh failed: {str(e)}")

@app.get("/api/url")
async def analyze_url(url: str, client_id: str = "default"):
    """Analyze Spotify URL and return song information"""
    logger.info(f"Analyzing URL: {url}")
    
    try:
        # Store URL for this client
        client_urls[client_id] = url
        
        # Get real Spotify data using browser auth (try cached first, then refresh if needed)
        spotify_auth = get_spotify_browser_auth()
        if not spotify_auth:
            # Try refreshing authentication if cached version failed
            print("Cached authentication expired, refreshing...")
            spotify_auth = get_spotify_browser_auth(force_refresh=True)
            if not spotify_auth:
                raise HTTPException(status_code=500, detail="Spotify authentication failed - please try again")
        
        # Extract playlist ID
        import re
        patterns = [
            r"spotify\.com/(playlist|album|track)/([a-zA-Z0-9]+)",
            r"spotify:(playlist|album|track):([a-zA-Z0-9]+)"
        ]
        
        playlist_id = None
        url_type = None
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                url_type = match.group(1)
                playlist_id = match.group(2)
                break
        
        if not playlist_id:
            raise HTTPException(status_code=400, detail="Invalid Spotify URL")
        
        # Get data based on URL type
        if url_type == "playlist":
            playlist_data = spotify_auth.get(f"playlists/{playlist_id}")
            tracks_response = spotify_auth.list(f"playlists/{playlist_id}/tracks")
            
            # Store playlist info
            playlist_info[client_id] = {
                "name": playlist_data["name"],
                "author": playlist_data.get("owner", {}).get("display_name", "Unknown"),
                "total_tracks": playlist_data["tracks"]["total"]
            }
            
            # Process tracks
            songs = []
            for item in tracks_response:  # Get all tracks
                track = item.get("track")
                if track and track.get("name"):
                    song_data = {
                        "song_id": track["id"],
                        "name": track["name"],
                        "artist": ", ".join([artist["name"] for artist in track.get("artists", [])]),
                        "album_name": track.get("album", {}).get("name", "Unknown Album"),
                        "cover_url": track.get("album", {}).get("images", [{}])[0].get("url", "") if track.get("album", {}).get("images") else "",
                        "url": track.get("external_urls", {}).get("spotify", ""),
                        "explicit": track.get("explicit", False)
                    }
                    songs.append(song_data)
            
            # Store songs data for this client
            client_songs[client_id] = songs
            
            # Return both playlist info and songs
            response_data = {
                "playlist_info": playlist_info[client_id],
                "songs": songs
            }
            return JSONResponse(content=response_data)
            
        elif url_type == "album":
            album_data = spotify_auth.get(f"albums/{playlist_id}")
            tracks_response = spotify_auth.list(f"albums/{playlist_id}/tracks")
            
            # Store album info as playlist
            playlist_info[client_id] = {
                "name": album_data["name"],
                "author": ", ".join([artist["name"] for artist in album_data.get("artists", [])]),
                "total_tracks": album_data["total_tracks"]
            }
            
            # Process tracks
            songs = []
            for track in tracks_response:
                if track and track.get("name"):
                    song_data = {
                        "song_id": track["id"],
                        "name": track["name"],
                        "artist": ", ".join([artist["name"] for artist in track.get("artists", [])]),
                        "album_name": album_data["name"],
                        "cover_url": album_data.get("images", [{}])[0].get("url", "") if album_data.get("images") else "",
                        "url": track.get("external_urls", {}).get("spotify", ""),
                        "explicit": track.get("explicit", False)
                    }
                    songs.append(song_data)
            
            # Return both playlist info and songs
            response_data = {
                "playlist_info": playlist_info[client_id],
                "songs": songs
            }
            return JSONResponse(content=response_data)
            
        elif url_type == "track":
            track_data = spotify_auth.get(f"tracks/{playlist_id}")
            
            # Store track info as single-song playlist
            playlist_info[client_id] = {
                "name": track_data["name"],
                "author": ", ".join([artist["name"] for artist in track_data.get("artists", [])]),
                "total_tracks": 1
            }
            
            song_data = {
                "song_id": track_data["id"],
                "name": track_data["name"],
                "artist": ", ".join([artist["name"] for artist in track_data.get("artists", [])]),
                "album_name": track_data.get("album", {}).get("name", "Unknown Album"),
                "cover_url": track_data.get("album", {}).get("images", [{}])[0].get("url", "") if track_data.get("album", {}).get("images") else "",
                "url": track_data.get("external_urls", {}).get("spotify", ""),
                "explicit": track_data.get("explicit", False)
            }
            
            # Return both playlist info and songs
            response_data = {
                "playlist_info": playlist_info[client_id],
                "songs": [song_data]
            }
            return JSONResponse(content=response_data)
    
    except Exception as e:
        logger.error(f"Error analyzing URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/download/url")
async def download_from_url(request: DownloadRequest):
    """Download songs from URL with real-time progress updates"""
    logger.info(f"Starting download for client {request.client_id}: {request.url}")
    
    try:
        # Get the stored URL or use provided one
        download_url = client_urls.get(request.client_id, request.url)
        
        # Get playlist info if available
        playlist_data = playlist_info.get(request.client_id, {})
        
        # Send playlist started message
        if request.client_id in websocket_connections:
            total_tracks = playlist_data.get("total_tracks", 0)
            
            await websocket_connections[request.client_id].send_text(json.dumps({
                "type": "playlist_started",
                "playlist_name": playlist_data.get("name", "Playlist"),
                "playlist_author": playlist_data.get("author", "Unknown"),
                "total_tracks": total_tracks
            }))
        
        # Start multiprocessing download with progress queue
        songs_data = client_songs.get(request.client_id, [])
        
        # Create progress queue for this client
        progress_queue = multiprocessing.Queue()
        progress_queues[request.client_id] = progress_queue
        
        # Initialize skipped songs list for this client
        if request.client_id not in skipped_songs:
            skipped_songs[request.client_id] = []
        
        # Create shared manager for skipped songs
        manager = multiprocessing.Manager()
        skipped_songs_shared = manager.list()  # Shared list that can be modified from both processes
        
        # Start progress monitoring in background
        asyncio.create_task(monitor_progress_queue(request.client_id))
        
        # Start download in separate process with error handling
        if request.output_path:
            # Expand user path (~) and normalize path separators
            output_dir = os.path.expanduser(request.output_path.replace('/', os.sep))
        else:
            output_dir = os.path.join(os.path.expanduser("~"), "Downloads", "SpotDL")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Verify authentication is still valid before starting download
            spotify_auth = get_spotify_browser_auth()
            if not spotify_auth:
                # Try to refresh authentication
                print("Authentication expired, refreshing before download...")
                spotify_auth = get_spotify_browser_auth(force_refresh=True)
                if not spotify_auth:
                    raise HTTPException(status_code=401, detail="Authentication expired. Please refresh the page and try again.")
            
            # Get auth token from parent process to pass to subprocess
            auth_token = spotify_auth.access_token if spotify_auth else None
            
            download_process = multiprocessing.Process(
                target=download_with_progress_queue,
                args=(download_url, output_dir, progress_queue, songs_data, skipped_songs_shared, auth_token)
            )
            download_process.start()
            active_downloads[request.client_id] = download_process
            
            # Store the shared skipped songs reference for this client
            skipped_songs[request.client_id] = skipped_songs_shared
            
            print(f"Download process started for client {request.client_id}")
            return JSONResponse(content={
                "status": "started", 
                "message": "Download started with real-time progress",
                "total_songs": len(songs_data)
            })
            
        except Exception as e:
            logger.error(f"Failed to start download process: {e}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"Failed to start download: {str(e)}"}
            )
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cancel/song")
async def cancel_song(request: dict):
    """Cancel/skip a specific song from both UI and download process"""
    client_id = request.get("client_id")
    song_id = request.get("song_id")
    

    
    try:
        # Find song info for this song ID to get name for matching
        song_info = None
        if client_id in client_songs:
            for song in client_songs[client_id]:
                if song.get("song_id") == song_id:
                    song_info = song
                    break
        
        # Add song info to skipped list so download process will skip it
        if client_id in skipped_songs and song_info:
            # Use multiple formats to increase matching chances
            skip_entries = [
                f"{song_info['artist']} - {song_info['name']}",  # Standard format
                song_info['name'].lower().strip(),  # Just song name
                f"{song_info['artist'].split(',')[0]} - {song_info['name']}" if ',' in song_info['artist'] else f"{song_info['artist']} - {song_info['name']}"  # First artist only
            ]
            
            for skip_entry in skip_entries:
                if skip_entry not in skipped_songs[client_id]:
                    skipped_songs[client_id].append(skip_entry)
            
            logger.info(f"Skipping: {song_info['name']} - {song_info['artist']}")
        
        # Send cancellation message via WebSocket to hide this song from UI
        if client_id in websocket_connections:
            await websocket_connections[client_id].send_text(json.dumps({
                "song": {"song_id": song_id},
                "progress": 0,
                "status": "cancelled",
                "message": "Skipped"
            }))
            

            return JSONResponse(content={"status": "cancelled", "message": "Song skipped"})
            
    except Exception as e:
        logger.error(f"Error cancelling individual song: {e}")
    
    return JSONResponse(content={"status": "error", "message": "Could not cancel song"})

@app.post("/api/cancel/all")
async def cancel_all_downloads(request: dict):
    """Cancel the entire download process immediately"""
    client_id = request.get("client_id")
    
    # Terminate the download process for this client immediately
    if client_id in active_downloads:
        try:
            download_process = active_downloads[client_id]
            if download_process and download_process.is_alive():
                print(f"Cancelling download immediately for client {client_id}")
                
                # Try terminate first
                download_process.terminate()
                
                # Wait very briefly, then force kill
                try:
                    download_process.join(timeout=0.5)  # Very short timeout
                except:
                    pass
                    
                # Force kill if still alive
                if download_process.is_alive():
                    download_process.kill()
                    print(f"⚡ Force-killed download process for client {client_id}")
                    try:
                        download_process.join(timeout=0.5)
                    except:
                        pass
                
                # Remove from active downloads
                del active_downloads[client_id]
                
                # Clean up progress queue
                if client_id in progress_queues:
                    del progress_queues[client_id]
                
                # Send cancellation message via WebSocket
                if client_id in websocket_connections:
                    await websocket_connections[client_id].send_text(json.dumps({
                        "type": "all_cancelled",
                        "message": "Download cancelled immediately"
                    }))
                    
                return JSONResponse(content={"status": "cancelled", "message": "Download cancelled immediately"})
        except Exception as e:
            logger.error(f"Error cancelling downloads: {e}")
    
    return JSONResponse(content={"status": "error", "message": "No active download found"})

@app.post("/api/delete/song")
async def delete_downloaded_song(request: dict):
    """Delete a downloaded song file"""
    client_id = request.get("client_id")
    song_id = request.get("song_id")
    
    try:
        # Find song info
        song_info = None
        if client_id in client_songs:
            for song in client_songs[client_id]:
                if song["song_id"] == song_id:
                    song_info = song
                    break
        
        if not song_info:
            return JSONResponse(content={"status": "error", "message": "Song not found"})
        
        # Try to find and delete the file
        # Common file extensions for downloaded songs
        extensions = ['.mp3', '.flac', '.m4a', '.wav']
        
        # Get output directory (default or from request)
        output_dir = os.path.join(os.path.expanduser("~"), "Downloads", "SpotDL")
        
        # Create possible filename patterns
        artist_name = song_info['artist'].split(',')[0].strip()  # Take first artist
        song_name = song_info['name']
        
        # Clean filename (basic cleaning)
        import re
        def clean_filename(text):
            # Remove invalid filename characters
            return re.sub(r'[<>:"/\\|?*]', '', text).strip()
        
        clean_artist = clean_filename(artist_name)
        clean_song = clean_filename(song_name)
        
        possible_filenames = [
            f"{clean_artist} - {clean_song}",
            f"{clean_song}",
            f"{clean_artist}_{clean_song}",
            song_name,
            f"{artist_name} - {song_name}"
        ]
        
        deleted_files = []
        for filename_base in possible_filenames:
            for ext in extensions:
                file_path = os.path.join(output_dir, f"{filename_base}{ext}")
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        deleted_files.append(file_path)
                        print(f"Deleted: {file_path}")
                    except Exception as e:
                        print(f"Failed to delete {file_path}: {e}")
        
        if deleted_files:
            return JSONResponse(content={
                "status": "success", 
                "message": f"Deleted {len(deleted_files)} file(s)",
                "deleted_files": deleted_files
            })
        else:
            return JSONResponse(content={
                "status": "warning", 
                "message": "No matching files found to delete"
            })
            
    except Exception as e:
        logger.error(f"Error deleting song: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)})

@app.post("/select-folder")
async def select_folder():
    """Open a folder selection dialog"""
    try:
        # Create a root window and hide it
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        
        # Open folder selection dialog
        folder_path = filedialog.askdirectory(
            title="Select Download Folder",
            initialdir=os.path.expanduser("~/Downloads")
        )
        
        # Clean up the root window
        root.destroy()
        
        if folder_path:
            # Convert to forward slashes for consistency
            folder_path = folder_path.replace('\\', '/')
            return JSONResponse(content={"success": True, "path": folder_path})
        else:
            return JSONResponse(content={"success": False, "message": "No folder selected"})
    
    except Exception as e:
        logger.error(f"Error selecting folder: {e}")
        return JSONResponse(content={"success": False, "message": str(e)})

@app.get("/", response_class=HTMLResponse)
async def get_main_page():
    """Serve the custom web interface"""
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>spotDL</title>
    <link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20xmlns:svg='http://www.w3.org/2000/svg'%20width='430'%20height='430'%3E%3Cdefs%3E%3ClinearGradient%20id='svg_31'%20spreadMethod='pad'%3E%3Cstop%20id='jq_stop_9381'%20offset='0'%20stop-color='%23fff'/%3E%3Cstop%20id='jq_stop_4866'%20offset='1'%20stop-color='%23000'/%3E%3C/linearGradient%3E%3C/defs%3E%3Cg%20class='layer'%3E%3Ctitle%3ELayer%201%3C/title%3E%3Crect%20id='svg_20'%20width='0'%20height='0'%20x='-249.892'%20y='35.054'%20fill='%2306d622'%20stroke='%2305ce16'%20stroke-width='20'/%3E%3Ccircle%20id='svg_25'%20cx='215'%20cy='215'%20r='200'%20fill='%2322d662'%20stroke='%2316ce57'%20stroke-linejoin='round'%20stroke-width='30'/%3E%3Cpath%20id='svg_27'%20fill='url(%23svg_31)'%20fill-opacity='0'%20stroke='%23fff'%20stroke-linecap='round'%20stroke-linejoin='round'%20stroke-width='30'%20d='m215,81c74.033149,0%20134,59.966851%20134,134c0,74.033149%20-59.966851,134%20-134,134c-74.033149,0%20-134,-59.966851%20-134,-134'/%3E%3Cline%20id='svg_28'%20x1='215'%20x2='215'%20y1='81.828'%20y2='215'%20fill='none'%20stroke='%23fff'%20stroke-linecap='round'%20stroke-linejoin='round'%20stroke-width='30'/%3E%3Cline%20id='svg_29'%20x1='215'%20x2='255'%20y1='216.237'%20y2='175'%20fill='none'%20stroke='%23fff'%20stroke-linecap='round'%20stroke-linejoin='round'%20stroke-width='30'/%3E%3Cline%20id='svg_30'%20x1='215'%20x2='175'%20y1='216.774'%20y2='175.538'%20fill='none'%20stroke='%23fff'%20stroke-linecap='round'%20stroke-linejoin='round'%20stroke-width='30'/%3E%3Cpath%20id='svg_33'%20fill='url(%23svg_31)'%20fill-opacity='0'%20stroke='%2316ce57'%20stroke-linecap='round'%20stroke-linejoin='round'%20stroke-width='30'%20d='m171.075278,88.279578c-34.946237,11.290323%20-68.279571,36.017306%20-83.333335,82.258066'/%3E%3C/g%3E%3C/svg%3E" type="image/svg+xml">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #191414 0%, #121212 100%);
            color: #ffffff;
            min-height: 100vh;
            overflow-x: hidden; /* Prevent horizontal scrollbar */
            overflow-y: scroll; /* Always show vertical scrollbar to prevent layout shift */
        }
        
        .container {
            max-width: 1000px; /* Reduced from 1200px to 800px for narrower interface */
            margin: 0 auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            transition: transform 0.8s cubic-bezier(0.25, 0.1, 0.25, 1);
            transform: translateY(20vh);
            will-change: transform; /* Optimize for animations */
            backface-visibility: hidden; /* Prevent sub-pixel rendering issues */
        }
        
        .container.centered {
            transform: translateY(20vh);
        }
        
        .container.searching {
            transform: translateY(0);
            min-height: 100vh; /* Only add min-height when searching to accommodate results */
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 20px 0;
        }
        
        .title-container {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
            margin-bottom: 10px;
        }
        
        .logo {
            animation: pulse 2s ease-in-out infinite alternate;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            100% { transform: scale(1.1); }
        }
        
        .header h1 {
            font-size: 3rem;
            font-weight: bold;
            margin-bottom: 0;
            margin-top: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .input-section {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px 30px 0px 30px; /* Further reduced bottom padding to 0px */
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            transition: all 0.6s cubic-bezier(0.25, 0.1, 0.25, 1);
            will-change: padding, height;
        }
        
        .input-section.expanded {
            padding: 30px 30px 30px 30px; /* Add bottom padding when expanded */
        }
        
        .url-input-group {
            display: flex;
            gap: 15px;
            margin-bottom: 10px; /* Reduced from 20px to 10px */
        }
        
        .url-input {
            flex: 1;
            padding: 15px 20px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
        }
        
        .url-input:focus {
            outline: none;
            box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.5);
        }
        
        .analyze-btn, .download-btn {
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .analyze-btn {
            background: #1db954;
            color: white;
        }
        
        .analyze-btn:hover {
            background: #1aa34a;
            transform: translateY(-2px);
        }
        
        .download-btn {
            background: #27ae60;
            color: white;
            opacity: 1;
            visibility: visible;
            transform: translateY(0);
        }
        
        .download-btn:hover {
            background: #219a52;
            transform: translateY(-2px);
        }
        
        /* Visible state for fade-in animations */
        .visible {
            opacity: 1 !important;
            visibility: visible !important;
            transform: translateY(0) !important;
        }
        
        .download-btn:disabled {
            background: #7f8c8d;
            cursor: not-allowed;
            transform: none;
        }
        
        /* Download buttons container */
        .download-buttons {
            display: flex;
            gap: 15px;
            align-items: center;
            height: 0;
            overflow: hidden;
            transition: height 0.3s ease, padding 0.3s ease, margin 0.3s ease;
            padding: 0;
            margin: 0;
        }
        
        .download-buttons.visible {
            height: auto;
            padding: 15px 0 0 0;
            margin: 10px 0 0 0;
        }
        
        .cancel-btn {
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            background: #e74c3c;
            color: white;
            opacity: 0;
            transform: scale(0.9);
        }
        
        .cancel-btn:hover {
            background: #c0392b;
            transform: translateY(-2px) scale(1);
        }
        
        .cancel-btn.show {
            opacity: 1;
            transform: scale(1);
        }
        
        /* Path Selection */
        .path-selection {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: transparent;
            padding: 12px 0; /* Increased from 4px to 12px for bigger invisible box */
            margin: 15px 0 8px 0;  /* Increased top margin for better spacing */
        }
        
        .path-info {
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 1;
            color: rgba(255, 255, 255, 0.9);
        }
        
        .path-icon {
            font-size: 18px;
        }
        
        .path-label {
            font-weight: 500;
            font-size: 14px;
        }
        
        .path-text {
            font-family: monospace;
            font-size: 13px;
            color: white;
        }
        
        .change-btn {
            background: #1db954;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: background 0.3s ease;
        }
        
        .change-btn:hover {
            background: #1aa34a;
            transform: translateY(-1px);
        }
        
        .loading {
            opacity: 0.6;
            pointer-events: none;
        }
        
        /* Results section - aligned to top */
        .results-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            margin-top: 0; /* Remove centering */
            transition: all 0.6s cubic-bezier(0.25, 0.1, 0.25, 1);
        }
        
        .playlist-header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        }
        
        .playlist-info h2 {
            font-size: 1.8rem;
            margin-bottom: 5px;
        }
        
        .playlist-info p {
            opacity: 0.8;
            font-size: 1rem;
        }
        
        .progress-counter {
            margin-left: auto;
            background: rgba(255, 255, 255, 0.1);
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
        }
        
        .songs-container {
            display: flex;
            flex-direction: column;
            gap: 15px;
            max-height: 600px;
            overflow-y: auto;
            padding-right: 10px;
        }
        
        .songs-container::-webkit-scrollbar {
            width: 8px;
        }
        
        .songs-container::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }
        
        .songs-container::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.3);
            border-radius: 4px;
        }
        
        .songs-container::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.5);
        }
        
        .song-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 20px;
            transition: all 0.3s ease;
            opacity: 0;
            transform: translateY(20px);
            animation: slideIn 0.5s ease forwards;
        }
        
        @keyframes slideIn {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .song-cover {
            width: 80px;
            height: 80px;
            border-radius: 8px;
            object-fit: cover;
        }
        
        .song-info {
            flex: 1;
        }
        
        .song-title {
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .song-artist {
            opacity: 0.8;
            margin-bottom: 5px;
        }
        
        .song-album {
            opacity: 0.6;
            font-size: 0.9rem;
        }
        
        .song-progress {
            min-width: 200px;
            text-align: right;
        }
        
        .progress-bar {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            height: 8px;
            margin-bottom: 8px;
            overflow: hidden;
        }
        
        .progress-fill {
            background: linear-gradient(90deg, #27ae60, #2ecc71);
            height: 100%;
            width: 0%;
            transition: width 0.3s ease;
            border-radius: 10px;
        }
        
        .progress-text {
            font-size: 0.9rem;
            font-weight: bold;
        }
        
        .delete-btn {
            background: rgba(231, 76, 60, 0.8);
            color: white;
            border: none;
            border-radius: 50%;
            width: 35px;
            height: 35px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }
        
        .delete-btn:hover {
            background: #e74c3c;
            transform: scale(1.1);
        }
        
        .status-completed {
            background: rgba(39, 174, 96, 0.2);
            border-left: 4px solid #27ae60;
        }
        
        .status-downloading {
            background: rgba(52, 152, 219, 0.2);
            border-left: 4px solid #3498db;
        }
        
        .status-error {
            background: rgba(231, 76, 60, 0.2);
            border-left: 4px solid #e74c3c;
        }
        
        .hidden {
            opacity: 0;
            visibility: hidden;
            transform: translateY(10px);
            transition: all 0.5s cubic-bezier(0.25, 0.1, 0.25, 1);
        }
        
        /* Confirmation Dialog */
        .confirmation-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(25, 20, 20, 0.85);
            backdrop-filter: blur(10px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }
        
        .confirmation-overlay.show {
            opacity: 1;
            pointer-events: all;
        }
        
        .confirmation-dialog {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.08));
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            padding: 40px;
            max-width: 450px;
            width: 90%;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
            transform: scale(0.9) translateY(20px);
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        
        .confirmation-overlay.show .confirmation-dialog {
            transform: scale(1) translateY(0);
        }
        
        .confirmation-title {
            font-size: 1.6rem;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ff6b6b;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .confirmation-message {
            margin-bottom: 25px;
            color: #ffffff;
            line-height: 1.6;
            font-size: 1.1rem;
            opacity: 0.95;
        }
        
        .confirmation-checkbox {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            margin-bottom: 30px;
            font-size: 0.95rem;
            color: rgba(255, 255, 255, 0.8);
        }
        
        .confirmation-checkbox input[type="checkbox"] {
            width: 18px;
            height: 18px;
            accent-color: #1db954;
        }
        
        .confirmation-buttons {
            display: flex;
            gap: 20px;
            justify-content: center;
        }
        
        .confirm-btn, .cancel-dialog-btn {
            padding: 15px 30px;
            border: none;
            border-radius: 12px;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            min-width: 120px;
        }
        
        .confirm-btn {
            background: linear-gradient(135deg, #ff6b6b, #ee5a52);
            color: white;
            box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
        }
        
        .confirm-btn:hover {
            background: linear-gradient(135deg, #ff5252, #d32f2f);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
        }
        
        .cancel-dialog-btn {
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .cancel-dialog-btn:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
        }
        
        /* Toast Notifications */
        .toast-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 2000;
            display: flex;
            flex-direction: column;
            gap: 15px;
            pointer-events: none;
        }
        
        .toast {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.08));
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 15px;
            padding: 20px 25px;
            min-width: 300px;
            max-width: 450px;
            color: white;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            transform: translateX(400px);
            opacity: 0;
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            pointer-events: all;
            position: relative;
        }
        
        .toast.show {
            transform: translateX(0);
            opacity: 1;
        }
        
        .toast.success {
            border-left: 4px solid #1db954;
        }
        
        .toast.success .toast-icon {
            color: #1db954;
        }
        
        .toast.info {
            border-left: 4px solid #3498db;
        }
        
        .toast.info .toast-icon {
            color: #3498db;
        }
        
        .toast-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        
        .toast-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: bold;
            font-size: 1rem;
        }
        
        .toast-icon {
            font-size: 1.2rem;
        }
        
        .toast-close {
            background: none;
            border: none;
            color: rgba(255, 255, 255, 0.7);
            font-size: 1.2rem;
            cursor: pointer;
            padding: 0;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: all 0.3s ease;
        }
        
        .toast-close:hover {
            background: rgba(255, 255, 255, 0.1);
            color: white;
        }
        
        .toast-message {
            color: rgba(255, 255, 255, 0.9);
            line-height: 1.4;
        }
        
        @media (max-width: 768px) {
            .toast-container {
                top: 10px;
                right: 10px;
                left: 10px;
                align-items: center;
            }
            
            .toast {
                min-width: unset;
                max-width: 100%;
                width: 100%;
            }
        }
        
        @media (max-width: 768px) {
            .url-input-group {
                flex-direction: column;
            }
            
            .song-card {
                flex-direction: column;
                text-align: center;
            }
            
            .song-progress {
                min-width: unset;
                width: 100%;
            }
            
            .download-buttons {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="title-container">
                <div class="logo">
                    <svg width="50" height="50" viewBox="0 0 430 430" xmlns="http://www.w3.org/2000/svg">
                        <defs>
                            <linearGradient id="svg_31" spreadMethod="pad">
                                <stop id="jq_stop_9381" offset="0" stop-color="#fff"/>
                                <stop id="jq_stop_4866" offset="1" stop-color="#000"/>
                            </linearGradient>
                        </defs>
                        <g class="layer">
                            <title>Layer 1</title>
                            <rect id="svg_20" width="0" height="0" x="-249.892" y="35.054" fill="#06d622" stroke="#05ce16" stroke-width="20"/>
                            <circle id="svg_25" cx="215" cy="215" r="200" fill="#22d662" stroke="#16ce57" stroke-linejoin="round" stroke-width="30"/>
                            <path id="svg_27" fill="url(#svg_31)" fill-opacity="0" stroke="#fff" stroke-linecap="round" stroke-linejoin="round" stroke-width="30" d="m215,81c74.033149,0 134,59.966851 134,134c0,74.033149 -59.966851,134 -134,134c-74.033149,0 -134,-59.966851 -134,-134"/>
                            <line id="svg_28" x1="215" x2="215" y1="81.828" y2="215" fill="none" stroke="#fff" stroke-linecap="round" stroke-linejoin="round" stroke-width="30"/>
                            <line id="svg_29" x1="215" x2="255" y1="216.237" y2="175" fill="none" stroke="#fff" stroke-linecap="round" stroke-linejoin="round" stroke-width="30"/>
                            <line id="svg_30" x1="215" x2="175" y1="216.774" y2="175.538" fill="none" stroke="#fff" stroke-linecap="round" stroke-linejoin="round" stroke-width="30"/>
                            <path id="svg_33" fill="url(#svg_31)" fill-opacity="0" stroke="#16ce57" stroke-linecap="round" stroke-linejoin="round" stroke-width="30" d="m171.075278,88.279578c-34.946237,11.290323 -68.279571,36.017306 -83.333335,82.258066"/>
                        </g>
                    </svg>
                </div>
                <h1>spotDL</h1>
            </div>
            <p>Download your individual Spotify songs or playlist with all their metadata</p>
        </header>
        
        <div class="input-section">
            <div class="url-input-group">
                <input type="text" class="url-input" id="urlInput" placeholder="Enter Spotify playlist or track URL...">
                <button class="analyze-btn" id="analyzeBtn">Search</button>
            </div>
            
            <!-- Download Path Selection -->
            <div class="path-selection">
                <div class="path-info">
                    <span class="path-label">Downloads:</span>
                    <span class="path-text" id="downloadPath">~/Downloads/SpotDL</span>
                </div>
                <button class="change-btn" id="changePathBtn">Change</button>
            </div>
            
            <div class="download-buttons">
                <button class="download-btn hidden" id="downloadBtn" disabled>Start Download</button>
                <button class="cancel-btn hidden" id="cancelBtn">Cancel</button>
            </div>
        </div>
        
        <div class="results-section hidden" id="resultsSection">
            <div class="playlist-header">
                <div class="playlist-info">
                    <h2 id="playlistTitle">Playlist</h2>
                    <p id="playlistAuthor">by Unknown</p>
                    <p id="downloadLocation" style="font-size: 0.9em; opacity: 0.8; margin-top: 8px;"> Downloads: C:/Users/karol/Downloads/SpotDL</p>
                </div>
                <div class="progress-counter" id="progressCounter">0 / 0 completed</div>
            </div>
            <div class="songs-container" id="songsContainer"></div>
        </div>
    </div>
    
    <!-- Confirmation Dialog -->
    <div class="confirmation-overlay" id="confirmationOverlay">
        <div class="confirmation-dialog">
            <div class="confirmation-title">Delete Song</div>
            <div class="confirmation-message" id="confirmationMessage">
                Are you sure you want to delete this downloaded song?
            </div>
            <div class="confirmation-checkbox">
                <input type="checkbox" id="dontShowAgain">
                <label for="dontShowAgain">Don't show this message again</label>
            </div>
            <div class="confirmation-buttons">
                <button class="confirm-btn" id="confirmDeleteBtn">Yes, Delete</button>
                <button class="cancel-dialog-btn" id="cancelDialogBtn">Cancel</button>
            </div>
        </div>
    </div>
    
    <!-- Toast Container -->
    <div class="toast-container" id="toastContainer"></div>
    
    <script>
        let websocket = null;
        let currentSongs = [];
        let completedCount = 0;
        let totalCount = 0;
        let completedSongs = new Set();  // Track which songs have been marked complete
        let currentDownloadPath = "~/Downloads/SpotDL";
        let isDownloading = false;
        let showDeleteConfirmation = true; // User preference for delete confirmation
        let pendingDeleteSongId = null; // Store song ID pending deletion
        let toastCounter = 0; // Counter for unique toast IDs
        
        // WebSocket connection
        async function refreshAuthentication() {
            try {
                const response = await fetch('/api/refresh-auth', { method: 'POST' });
                if (response.ok) {
                    showToast('Authentication Refreshed', 'Spotify authentication has been renewed successfully!', 'success');
                    return true;
                } else {
                    throw new Error('Failed to refresh authentication');
                }
            } catch (error) {
                showToast('Authentication Failed', 'Failed to refresh authentication. Please reload the page.', 'info');
                return false;
            }
        }

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const clientId = 'web_client_' + Math.random().toString(36).substr(2, 9);
            websocket = new WebSocket(`${protocol}//${window.location.host}/api/ws?client_id=${clientId}`);
            
            websocket.onopen = function(event) {
                console.log('WebSocket connected');
            };
            
            websocket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                console.log('WebSocket message:', data);
                
                if (data.type === 'playlist_started') {
                    updatePlaylistInfo(data.playlist_name, data.playlist_author, data.total_tracks);
                } else if (data.type === 'all_cancelled' || data.type === 'download_cancelled') {
                    // Handle download cancellation
                    // Don't reset button here as we already did it in cancelDownload
                    showToast('Download Cancelled', 'All downloads have been cancelled successfully.', 'success');
                } else if (data.song) {
                    updateSongProgress(data);
                    
                    // Check if all songs are complete to reset download button
                    if (completedCount >= totalCount && totalCount > 0 && isDownloading) {
                        setTimeout(() => {
                            resetDownloadButton();
                            // Show completion toast
                            showToast('Download Complete!', `Successfully downloaded ${completedCount} songs.`, 'success');
                        }, 1000); // Small delay to let final updates complete
                    }
                }
            };
            
            websocket.onclose = function(event) {
                console.log('WebSocket disconnected');
                setTimeout(connectWebSocket, 3000); // Reconnect after 3 seconds
            };
            
            window.clientId = clientId;
        }
        
        // UI Functions
        function updatePlaylistInfo(name, author, total) {
            document.getElementById('playlistTitle').textContent = name;
            document.getElementById('playlistAuthor').textContent = `by ${author}`;
            totalCount = total;
            updateProgressCounter();
        }
        
        function updateProgressCounter() {
            document.getElementById('progressCounter').textContent = `${completedCount} / ${totalCount} completed`;
        }
        
        function addSongCard(song, index) {
            const container = document.getElementById('songsContainer');
            const card = document.createElement('div');
            card.className = 'song-card';
            card.id = `song-${song.song_id}`;
            card.style.animationDelay = `${index * 0.1}s`;
            
            card.innerHTML = `
                <img src="${song.cover_url}" alt="Album Cover" class="song-cover">
                <div class="song-info">
                    <div class="song-title">${song.name}</div>
                    <div class="song-artist">${song.artist}</div>
                    <div class="song-album">${song.album_name}</div>
                </div>
                <div class="song-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-${song.song_id}"></div>
                    </div>
                    <div class="progress-text" id="text-${song.song_id}">Queued</div>
                </div>
                <button class="delete-btn" onclick="removeSong('${song.song_id}')">×</button>
            `;
            
            container.appendChild(card);
            
            // Animate in after a delay
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        }
        
        // Progress animation system
        const progressAnimations = new Map();
        
        function startProgressAnimation(songId) {
            // Stop any existing animation for this song
            if (progressAnimations.has(songId)) {
                clearInterval(progressAnimations.get(songId).interval);
            }
            
            const progressFill = document.getElementById(`progress-${songId}`);
            if (!progressFill) return;
            
            let currentProgress = 0;
            const maxProgress = 90; // Stop at 90% until download completes
            const increment = 2; // 2% every 0.5 seconds
            const intervalTime = 500; // 0.5 seconds
            
            const animationData = {
                currentProgress: 0,
                isCompleted: false,
                interval: null
            };
            
            animationData.interval = setInterval(() => {
                if (animationData.isCompleted) {
                    clearInterval(animationData.interval);
                    return;
                }
                
                if (animationData.currentProgress < maxProgress) {
                    animationData.currentProgress += increment;
                    progressFill.style.width = `${animationData.currentProgress}%`;
                }
                // If we reach 90%, the interval continues but progress stops incrementing
                // until completeProgressAnimation is called
            }, intervalTime);
            
            progressAnimations.set(songId, animationData);
        }
        
        function completeProgressAnimation(songId) {
            const animationData = progressAnimations.get(songId);
            if (animationData) {
                animationData.isCompleted = true;
                clearInterval(animationData.interval);
                
                // Jump to 100%
                const progressFill = document.getElementById(`progress-${songId}`);
                if (progressFill) {
                    progressFill.style.width = '100%';
                }
            }
        }
        
        function stopProgressAnimation(songId) {
            const animationData = progressAnimations.get(songId);
            if (animationData) {
                clearInterval(animationData.interval);
                progressAnimations.delete(songId);
            }
        }

        function updateSongProgress(data) {
            let songId = data.song.song_id;
            let progressFill = document.getElementById(`progress-${songId}`);
            let progressText = document.getElementById(`text-${songId}`);
            let songCard = document.getElementById(`song-${songId}`);
            
            // Fallback: if song_id is unknown and we have current_index, try to find by position
            if (songId && songId.startsWith('unknown-') && data.song.current_index) {
                const currentIndex = data.song.current_index - 1; // Convert to 0-based index
                const allSongCards = document.querySelectorAll('.song-card');
                
                if (currentIndex >= 0 && currentIndex < allSongCards.length) {
                    const targetCard = allSongCards[currentIndex];
                    if (targetCard && targetCard.id.startsWith('song-')) {
                        songId = targetCard.id.replace('song-', '');
                        progressFill = document.getElementById(`progress-${songId}`);
                        progressText = document.getElementById(`text-${songId}`);
                        songCard = targetCard;
                        console.log(`Fallback: Using position-based song ID ${songId} for index ${data.song.current_index}`);
                    }
                }
            }
            
            console.log(`Updating song ${songId}: ${data.status} - ${data.progress * 100}%`);
            
            // Add detailed debug info for troubleshooting
            if (!progressFill || !progressText || !songCard) {
                console.warn(`Missing elements for ${songId}:`, {
                    progressFill: !!progressFill,
                    progressText: !!progressText, 
                    songCard: !!songCard,
                    originalSongId: data.song.song_id,
                    currentIndex: data.song.current_index,
                    status: data.status
                });
            }
            
            if (progressFill && progressText && songCard) {
                // Update status and styling based on download state
                songCard.className = 'song-card';
                
                if (data.status === 'downloading') {
                    songCard.classList.add('status-downloading');
                    progressText.textContent = 'Downloading...';
                    
                    // Start the incremental progress animation
                    startProgressAnimation(songId);
                    
                } else if (data.status === 'processing') {
                    songCard.classList.add('status-downloading');
                    progressText.textContent = 'Processing...';
                    
                    // Continue animation if it was already started
                    if (!progressAnimations.has(songId)) {
                        startProgressAnimation(songId);
                    }
                    
                } else if (data.status === 'success' || data.status === 'completed') {
                    songCard.classList.add('status-completed');
                    progressText.textContent = 'Download completed';
                    
                    // Complete the animation (jump to 100%)
                    completeProgressAnimation(songId);
                    
                    // Only increment if not already completed
                    if (!completedSongs.has(songId)) {
                        completedSongs.add(songId);
                        completedCount++;
                        updateProgressCounter();
                    }
                    
                } else if (data.status === 'exists') {
                    songCard.classList.add('status-completed');
                    progressText.textContent = 'Already downloaded';
                    
                    // Immediately set to 100% for existing files
                    progressFill.style.width = '100%';
                    
                    // Stop any running animation
                    stopProgressAnimation(songId);
                    
                    // Mark as completed
                    if (!completedSongs.has(songId)) {
                        completedSongs.add(songId);
                        completedCount++;
                        updateProgressCounter();
                    }

                    
                } else if (data.status === 'error') {
                    songCard.classList.add('status-error');
                    progressText.textContent = 'Download failed';
                    
                    // Stop any running animation
                    stopProgressAnimation(songId);
                    
                } else if (data.status === 'cancelled') {
                    // Hide the song card with animation
                    stopProgressAnimation(songId);
                    songCard.style.transition = 'all 0.3s ease';
                    songCard.style.opacity = '0';
                    songCard.style.transform = 'translateX(-100%)';
                    setTimeout(() => {
                        songCard.remove();
                    }, 300);
                }
            }
        }
        
        async function removeSong(songId) {
            const songCard = document.getElementById(`song-${songId}`);
            const progressText = document.getElementById(`text-${songId}`);
            
            if (!songCard) return;
            
            // Check if song is downloaded/completed
            const isCompleted = songCard.classList.contains('status-completed');
            
            if (isCompleted && showDeleteConfirmation) {
                // Show confirmation dialog for completed songs
                const songTitle = songCard.querySelector('.song-title').textContent;
                const songArtist = songCard.querySelector('.song-artist').textContent;
                
                document.getElementById('confirmationMessage').textContent = 
                    `Are you sure you want to delete "${songTitle}" by ${songArtist}?`;
                
                pendingDeleteSongId = songId;
                showConfirmationDialog(true);
                return;
            }
            
            // For non-completed songs or when confirmation is disabled, proceed directly
            await performRemoveSong(songId);
        }
        
        async function performRemoveSong(songId) {
            const songCard = document.getElementById(`song-${songId}`);
            const isCompleted = songCard && songCard.classList.contains('status-completed');
            
            if (songCard) {
                if (isCompleted) {
                    // Call delete API for completed songs
                    try {
                        const response = await fetch('/api/delete/song', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                client_id: window.clientId,
                                song_id: songId
                            })
                        });
                        
                        const result = await response.json();
                        if (result.status === 'success') {
                            const songTitle = songCard.querySelector('.song-title').textContent;
                            showToast('Song Deleted', `"${songTitle}" has been deleted from your library.`, 'success');
                        } else if (result.status === 'warning') {
                            showToast('File Not Found', result.message, 'info');
                        }
                    } catch (error) {
                        console.error('Error deleting song file:', error);
                    }
                } else {
                    // Call cancel API for non-completed songs
                    try {
                        await fetch('/api/cancel/song', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                client_id: window.clientId,
                                song_id: songId
                            })
                        });
                        
                        const songTitle = songCard.querySelector('.song-title').textContent;
                        showToast('Song Cancelled', `"${songTitle}" has been removed from the download queue.`, 'info');
                    } catch (error) {
                        console.error('Error cancelling song:', error);
                    }
                }
                
                // Remove from UI
                songCard.style.animation = 'none';
                songCard.style.transition = 'all 0.3s ease';
                songCard.style.opacity = '0';
                songCard.style.transform = 'translateX(-100%)';
                setTimeout(() => {
                    songCard.remove();
                }, 300);
            }
        }
        
        // Toast Notification Functions
        function showToast(title, message, type = 'success') {
            const toastId = 'toast-' + (++toastCounter);
            const toastContainer = document.getElementById('toastContainer');
            
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.id = toastId;
            
            toast.innerHTML = `
                <div class="toast-header">
                    <div class="toast-title">
                        ${title}
                    </div>
                    <button class="toast-close" onclick="closeToast('${toastId}')">×</button>
                </div>
                <div class="toast-message">${message}</div>
            `;
            
            toastContainer.appendChild(toast);
            
            // Trigger animation
            setTimeout(() => {
                toast.classList.add('show');
            }, 100);
            
            return toastId;
        }
        
        function closeToast(toastId) {
            const toast = document.getElementById(toastId);
            if (toast) {
                toast.classList.remove('show');
                setTimeout(() => {
                    toast.remove();
                }, 400);
            }
        }
        
        // Confirmation Dialog Functions
        function showConfirmationDialog(show) {
            const overlay = document.getElementById('confirmationOverlay');
            if (show) {
                overlay.classList.add('show');
            } else {
                overlay.classList.remove('show');
            }
        }
        
        // Cancel download functionality
        async function cancelDownload() {
            try {
                // Immediately show feedback and reset UI
                resetDownloadButton();
                showToast('Cancelling...', 'Stopping all downloads immediately.', 'info');
                
                const response = await fetch('/api/cancel/all', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        client_id: window.clientId
                    })
                });
                
                const result = await response.json();
                if (result.status === 'cancelled') {
                    console.log('Download cancelled successfully');
                } else {
                    console.error('Failed to cancel download:', result.message);
                    showToast('Cancellation Failed', 'Could not cancel downloads: ' + result.message, 'info');
                }
            } catch (error) {
                console.error('Error cancelling download:', error);
                showToast('Cancellation Error', 'Network error while cancelling downloads.', 'info');
            }
        }
        
        // API Functions
        async function analyzeUrl() {
            const url = document.getElementById('urlInput').value.trim();
            if (!url) {
                showToast('URL Required', 'Please enter a Spotify playlist or track URL.', 'info');
                return;
            }
            
            const analyzeBtn = document.getElementById('analyzeBtn');
            const downloadBtn = document.getElementById('downloadBtn');
            const resultsSection = document.getElementById('resultsSection');
            
            // Move interface to top before starting search
            moveInterfaceToTop();
            
            analyzeBtn.textContent = 'Searching...';
            analyzeBtn.classList.add('loading');
            
            try {
                const response = await fetch(`/api/url?url=${encodeURIComponent(url)}&client_id=${window.clientId}`);
                
                if (response.status === 500) {
                    const errorData = await response.json();
                    if (errorData.detail && errorData.detail.includes('authentication')) {
                        // Try to refresh authentication
                        if (confirm('Authentication expired. Would you like to refresh and try again?')) {
                            await refreshAuthentication();
                            // Retry the analysis
                            const retryResponse = await fetch(`/api/url?url=${encodeURIComponent(url)}&client_id=${window.clientId}`);
                            if (!retryResponse.ok) throw new Error('Failed to analyze URL after authentication refresh');
                            const data = await retryResponse.json();
                        } else {
                            throw new Error('Authentication required');
                        }
                    } else {
                        throw new Error('Failed to analyze URL');
                    }
                } else if (!response.ok) {
                    throw new Error('Failed to analyze URL');
                }
                
                const data = await response.json();
                const songs = data.songs;
                const playlistInfo = data.playlist_info;
                currentSongs = songs;
                
                // Update playlist info
                if (playlistInfo) {
                    document.getElementById('playlistTitle').textContent = playlistInfo.name;
                    document.getElementById('playlistAuthor').textContent = `by ${playlistInfo.author}`;
                }
                
                // Show results
                // Expand the input section smoothly
                const inputSection = document.querySelector('.input-section');
                inputSection.classList.add('expanded');
                
                // Fade in the results section and download button
                resultsSection.classList.remove('hidden');
                resultsSection.classList.add('visible');
                
                // Animate the download button in with a slight delay
                setTimeout(() => {
                    const downloadButtons = document.querySelector('.download-buttons');
                    downloadButtons.classList.add('visible');
                    downloadBtn.classList.remove('hidden');
                    downloadBtn.classList.add('visible');
                    downloadBtn.disabled = false;
                }, 200);
                
                // Clear previous songs
                document.getElementById('songsContainer').innerHTML = '';
                completedCount = 0;
                totalCount = playlistInfo ? playlistInfo.total_tracks : songs.length;
                updateProgressCounter();
                
                // Add songs one by one with animation delay
                songs.forEach((song, index) => {
                    setTimeout(() => {
                        addSongCard(song, index);
                    }, index * 150); // Stagger the appearance
                });
                
            } catch (error) {
                showToast('Analysis Failed', 'Error analyzing URL: ' + error.message, 'info');
            } finally {
                analyzeBtn.textContent = 'Search';
                analyzeBtn.classList.remove('loading');
            }
        }
        
        async function startDownload() {
            if (isDownloading) return;
            
            const url = document.getElementById('urlInput').value.trim();
            const downloadBtn = document.getElementById('downloadBtn');
            
            isDownloading = true;
            downloadBtn.textContent = 'Downloading...';
            downloadBtn.disabled = true;
            downloadBtn.classList.add('loading');
            
            // Show cancel button with animation
            const cancelBtn = document.getElementById('cancelBtn');
            cancelBtn.classList.remove('hidden');
            setTimeout(() => {
                cancelBtn.classList.add('show');
            }, 100);
            
            try {
                const response = await fetch('/api/download/url', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        url: url,
                        client_id: window.clientId,
                        output_path: currentDownloadPath
                    })
                });
                
                if (response.status === 401) {
                    // Authentication expired
                    if (confirm('Authentication expired. Would you like to refresh and try again?')) {
                        await refreshAuthentication();
                        // Retry the download - recursively call startDownload
                        resetDownloadButton();
                        await startDownload();
                        return;
                    } else {
                        throw new Error('Authentication required');
                    }
                } else if (!response.ok) {
                    throw new Error('Download failed');
                }
                
                const result = await response.json();
                console.log('Download completed:', result);
                
            } catch (error) {
                showToast('Download Failed', 'Download error: ' + error.message, 'info');
                resetDownloadButton();
            }
        }
        
        // Path change functionality
        async function changeDownloadPath() {
            try {
                const response = await fetch('/select-folder', { method: 'POST' });
                const data = await response.json();
                if (data.success && data.path) {
                    currentDownloadPath = data.path;
                    document.getElementById('downloadPath').textContent = currentDownloadPath;
                    document.getElementById('downloadLocation').textContent = `Downloads: ${currentDownloadPath}`;
                }
            } catch (error) {
                console.error('Error selecting folder:', error);
                // Fallback to prompt
                const newPath = prompt('Enter new download path:', currentDownloadPath);
                if (newPath && newPath.trim()) {
                    currentDownloadPath = newPath.trim();
                    document.getElementById('downloadPath').textContent = currentDownloadPath;
                    document.getElementById('downloadLocation').textContent = `Downloads: ${currentDownloadPath}`;
                }
            }
        }
        
        // Fix button text after download completion
        function resetDownloadButton() {
            const downloadBtn = document.getElementById('downloadBtn');
            const cancelBtn = document.getElementById('cancelBtn');
            
            downloadBtn.textContent = 'Start Download';
            downloadBtn.disabled = false;
            downloadBtn.classList.remove('loading');
            isDownloading = false;
            
            // Hide cancel button with animation
            cancelBtn.classList.remove('show');
            setTimeout(() => {
                cancelBtn.classList.add('hidden');
            }, 300);
        }
        
        // Function to reset interface to centered position
        function resetInterfacePosition() {
            const container = document.querySelector('.container');
            const resultsSection = document.getElementById('resultsSection');
            
            // If no results are visible, return to center
            if (resultsSection.classList.contains('hidden')) {
                container.classList.remove('searching');
                container.classList.add('centered');
            }
        }
        
        // Event listeners
        document.getElementById('analyzeBtn').addEventListener('click', analyzeUrl);
        document.getElementById('downloadBtn').addEventListener('click', startDownload);
        document.getElementById('cancelBtn').addEventListener('click', cancelDownload);
        document.getElementById('changePathBtn').addEventListener('click', changeDownloadPath);
        
        // Confirmation dialog event listeners
        document.getElementById('confirmDeleteBtn').addEventListener('click', async function() {
            if (document.getElementById('dontShowAgain').checked) {
                showDeleteConfirmation = false;
                // Note: This is session-based only, resets when server restarts
            }
            
            showConfirmationDialog(false);
            if (pendingDeleteSongId) {
                await performRemoveSong(pendingDeleteSongId);
                pendingDeleteSongId = null;
            }
        });
        
        document.getElementById('cancelDialogBtn').addEventListener('click', function() {
            showConfirmationDialog(false);
            pendingDeleteSongId = null;
        });
        
        // Close confirmation dialog when clicking outside
        document.getElementById('confirmationOverlay').addEventListener('click', function(e) {
            if (e.target === this) {
                showConfirmationDialog(false);
                pendingDeleteSongId = null;
            }
        });
        
        // Enter key support
        document.getElementById('urlInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                analyzeUrl();
            }
        });
        
        // Initialize WebSocket connection
        connectWebSocket();
        
        // Note: showDeleteConfirmation is session-based, always starts as true
        
        // Initialize interface positioning
        function initializeInterface() {
            const container = document.querySelector('.container');
            container.classList.add('centered');
        }
        
        function moveInterfaceToTop() {
            const container = document.querySelector('.container');
            container.classList.remove('centered');
            container.classList.add('searching');
        }
        
        // Initialize centered position on load
        initializeInterface();
        
        // Add double-click on title to reset interface
        document.querySelector('.header h1').addEventListener('dblclick', function() {
            // Clear results and reset position
            const resultsSection = document.getElementById('resultsSection');
            const downloadBtn = document.getElementById('downloadBtn');
            
            // Contract the input section
            const inputSection = document.querySelector('.input-section');
            inputSection.classList.remove('expanded');
            
            // Animate out the elements
            const downloadButtons = document.querySelector('.download-buttons');
            downloadButtons.classList.remove('visible');
            resultsSection.classList.remove('visible');
            downloadBtn.classList.remove('visible');
            
            // Wait for animation to complete before hiding
            setTimeout(() => {
                resultsSection.classList.add('hidden');
                downloadBtn.classList.add('hidden');
                resetInterfacePosition();
            }, 500);
        });
        
        // Test with example data on load (for demo)
        window.addEventListener('load', function() {
            // Auto-fill with example playlist URL for testing
            document.getElementById('urlInput').value = 'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M';
        });
    </script>
</body>
</html>
    """)

def handle_shutdown(signum, frame):
    """Signal handler for immediate shutdown"""
    print("\n Cancelling download immediately...")
    
    # Terminate all active download processes immediately
    for client_id, process in list(active_downloads.items()):
        if hasattr(process, 'terminate'):
            try:
                process.terminate()
                process.join(timeout=1)  # Wait up to 1 second
                if process.is_alive():
                    process.kill()  # Force kill if still alive
                print(f" Download process for {client_id} cancelled")
            except Exception as e:
                print(f" Error terminating process: {e}")
            finally:
                if client_id in active_downloads:
                    del active_downloads[client_id]
    
    # Clear all progress queues
    progress_queues.clear()
    
    if shutdown_event:
        shutdown_event.set()
    
    print("Shutdown complete")
    sys.exit(0)

def main():
    """Main function to start the web interface"""
    print("Starting SpotDL Web Interface...")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Detect if running as executable and disable colors
    is_executable = hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS')
    
    # Port finding with more attempts (tries 8807-8816 like original spotDL)
    try:
        available_port = find_available_port(8807, 10)
        web_url = f"http://127.0.0.1:{available_port}"
        print(f"Web interface: {web_url}")
        
        # Auto-open the web browser
        import webbrowser
        import threading
        
        def open_browser():
            import time
            time.sleep(1.5)  # Wait for server to start
            try:
                webbrowser.open(web_url)
                print(f"🔗 Opening browser at {web_url}")
            except Exception as e:
                print(f"Could not open browser automatically: {e}")
                print(f"Please manually open: {web_url}")
        
        # Start browser opener in background thread
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        try:
            uvicorn.run(
                app,
                host="127.0.0.1",  # Use 127.0.0.1 like original spotDL
                port=available_port,
                log_level="warning",  # Reduce log verbosity further
                use_colors=not is_executable,  # Disable colors in executable
                access_log=False,  # Reduce log verbosity
                server_header=False,  # Hide server headers
                date_header=False     # Hide date headers
            )
        except KeyboardInterrupt:
            print("\nServer stopped gracefully")
            return
    except RuntimeError as e:
        print(f"Error starting server: {e}")
        print("💡 Try closing applications using ports 8807-8816")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nServer stopped")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()