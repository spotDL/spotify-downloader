import logging
from typing import Optional

import yt_dlp

# Use the project logger configured via init_logging
logger = logging.getLogger("spotdl")


def get_best_audio_format(video_url: str, cookies_path: Optional[str] = None) -> str:
    """
    Determine the best YouTube audio format available for a given video.
    If Premium formats (e.g., high-bitrate Opus) are available using the cookies,
    return the appropriate yt_dlp format string to download them.
    Otherwise, return the default 'bestaudio/best'.

    Args:
        video_url (str): The YouTube video URL.
        cookies_path (Optional[str]): Path to cookies.txt file (optional).

    Returns:
        str: The best audio format string for yt_dlp.
    """

    logger.info(f"[YT Premium Detection] Checking formats for: {video_url}")

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "nocheckcertificate": True,
    }

    if cookies_path:
        ydl_opts["cookiefile"] = cookies_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            formats = info.get("formats", [])

            if not formats:
                logger.debug("No formats found for video.")
                return "bestaudio/best"

            # Look for premium-level formats (high-bitrate Opus)
            premium_formats = [
                f
                for f in formats
                if f.get("acodec") == "opus" and f.get("abr", 0) >= 160
            ]

            if premium_formats:
                best = max(premium_formats, key=lambda f: f.get("abr", 0))
                logger.info(
                    f"YouTube Premium detected — downloading {best.get('abr')}kbps Opus format."
                )
                return f"{best['format_id']}/bestaudio/best"

            # Fallback to standard formats
            logger.info("Regular YouTube account — downloading standard audio.")
            return "bestaudio/best"

    except Exception as e:
        logger.debug(f"Premium detection failed for {video_url}: {e}")
        return "bestaudio/best"


def detect_youtube_premium(cookies_path: str) -> bool:
    """
    Detect if the provided YouTube cookies belong to a Premium account.
    Returns True if Premium-quality formats appear available, False otherwise.
    """

    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "nocheckcertificate": True,
        "cookiefile": cookies_path,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
            formats = info.get("formats", [])

            premium_formats = [
                f
                for f in formats
                if f.get("acodec") == "opus" and f.get("abr", 0) >= 160
            ]

            if premium_formats:
                best = max(premium_formats, key=lambda f: f.get("abr", 0))
                logger.info(
                    f"YouTube Premium detected — premium audio available ({best.get('abr')}kbps opus)."
                )
                return True
    except Exception as exc:
        logger.debug(f"Premium detection check failed: {exc}")

    return False
