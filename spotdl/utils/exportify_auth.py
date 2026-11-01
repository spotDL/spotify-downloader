"""
Exportify Authentication module for spotDL.

Bypasses Spotify Web API's 403 Forbidden limitations on Development Mode apps
by using the public, production-approved Exportify Client ID with the PKCE flow.
"""

import logging
import os
from pathlib import Path
from typing import Any

import spotipy
from spotipy.cache_handler import CacheFileHandler
from spotipy.oauth2 import SpotifyPKCE

from spotdl.utils.config import get_spotdl_path

logger = logging.getLogger(__name__)

EXPORTIFY_CLIENT_ID = "9950ac751e34487dbbe027c4fd7f8e99"
EXPORTIFY_REDIRECT_URI = "https://watsonbox.github.io/exportify/"
EXPORTIFY_SCOPES = "user-library-read,playlist-read-private"


def get_exportify_client() -> spotipy.Spotify:
    """
    Initializes and returns a Spotipy client authenticated via Exportify's Client ID.
    If a valid token exists in the cache, it is reused and refreshed automatically.
    Otherwise, the user is guided through the interactive browser login.
    """
    cache_path = get_spotdl_path() / ".spotipy_exportify"

    # Ensure cache directory exists
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    cache_handler = CacheFileHandler(cache_path=str(cache_path))

    auth_manager = SpotifyPKCE(
        client_id=EXPORTIFY_CLIENT_ID,
        redirect_uri=EXPORTIFY_REDIRECT_URI,
        scope=EXPORTIFY_SCOPES,
        cache_handler=cache_handler,
    )

    # Check if token is already cached
    token_info = auth_manager.get_cached_token()

    if not token_info:
        logger.warning(
            "\n"
            "┌────────────────────────────────────────────────────────┐\n"
            "│  SPOTIFY AUTHENTICATION REQUIRED (via Exportify app)   │\n"
            "│                                                        │\n"
            "│  To access your saved/liked tracks, we need to log in  │\n"
            "│  using Exportify's production-approved Spotify app.   │\n"
            "│                                                        │\n"
            "│  1. A browser window will open for Spotify login.      │\n"
            "│  2. Log in and authorize access.                       │\n"
            "│  3. You will be redirected to watsonbox.github.io.     │\n"
            "│  4. Copy the entire redirect URL from your browser     │\n"
            "│     address bar and paste it in the prompt below.      │\n"
            "└────────────────────────────────────────────────────────┘\n"
        )

    try:
        # Get the access token (opens browser and prompts if not cached/expired)
        access_token = auth_manager.get_access_token()
    except Exception as exc:
        logger.error("Failed to authenticate with Spotify PKCE: %s", exc)
        raise exc

    return spotipy.Spotify(auth=access_token)
