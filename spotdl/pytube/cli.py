#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A simple command line application to download youtube videos."""
import argparse
import datetime as dt
import gzip
import json
import logging
import os
import shutil
import subprocess  # nosec
import sys
from typing import List
from typing import Optional

from pytube import __version__
from pytube import CaptionQuery
from pytube import Playlist
from pytube import Stream
from pytube import YouTube
from pytube.exceptions import PytubeError
from pytube.helpers import safe_filename
from pytube.helpers import setup_logger


def main():
    """Command line application to download youtube videos."""
    # noinspection PyTypeChecker
    parser = argparse.ArgumentParser(description=main.__doc__)
    args = _parse_args(parser)
    if args.verbosity:
        log_level = min(args.verbosity, 4) * 10
        setup_logger(logging.FATAL - log_level)

    if not args.url or "youtu" not in args.url:
        parser.print_help()
        sys.exit(1)

    if "/playlist" in args.url:
        print("Loading playlist...")
        playlist = Playlist(args.url)
        if not args.target:
            args.target = safe_filename(playlist.title())
        for youtube_video in playlist.videos:
            try:
                _perform_args_on_youtube(youtube_video, args)
            except PytubeError as e:
                print(f"There was an error with video: {youtube_video}")
                print(e)
    else:
        print("Loading video...")
        youtube = YouTube(args.url)
        _perform_args_on_youtube(youtube, args)


def _perform_args_on_youtube(
    youtube: YouTube, args: argparse.Namespace
) -> None:
    if args.list:
        display_streams(youtube)
    if args.build_playback_report:
        build_playback_report(youtube)
    if args.itag:
        download_by_itag(youtube=youtube, itag=args.itag, target=args.target)
    if hasattr(args, "caption_code"):
        download_caption(
            youtube=youtube, lang_code=args.caption_code, target=args.target
        )
    if args.resolution:
        download_by_resolution(
            youtube=youtube, resolution=args.resolution, target=args.target
        )
    if args.audio:
        download_audio(
            youtube=youtube, filetype=args.audio, target=args.target
        )
    if args.ffmpeg:
        ffmpeg_process(
            youtube=youtube, resolution=args.ffmpeg, target=args.target
        )


def _parse_args(
    parser: argparse.ArgumentParser, args: Optional[List] = None
) -> argparse.Namespace:
    parser.add_argument(
        "url", help="The YouTube /watch or /playlist url", nargs="?"
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__,
    )
    parser.add_argument(
        "--itag", type=int, help="The itag for the desired stream",
    )
    parser.add_argument(
        "-r",
        "--resolution",
        type=str,
        help="The resolution for the desired stream",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help=(
            "The list option causes pytube cli to return a list of streams "
            "available to download"
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbosity",
        help="Verbosity level, use up to 4 to increase logging -vvvv",
    )
    parser.add_argument(
        "--build-playback-report",
        action="store_true",
        help="Save the html and js to disk",
    )
    parser.add_argument(
        "-c",
        "--caption-code",
        type=str,
        default=argparse.SUPPRESS,
        nargs="?",
        help=(
            "Download srt captions for given language code. "
            "Prints available language codes if no argument given"
        ),
    )
    parser.add_argument(
        "-t",
        "--target",
        help=(
            "The output directory for the downloaded stream. "
            "Default is current working directory"
        ),
    )
    parser.add_argument(
        "-a",
        "--audio",
        const="mp4",
        nargs="?",
        help=(
            "Download the audio for a given URL at the highest bitrate available"
            "Defaults to mp4 format if none is specified"
        ),
    )
    parser.add_argument(
        "-f",
        "--ffmpeg",
        const="best",
        nargs="?",
        help=(
            "Downloads the audio and video stream for resolution provided"
            "If no resolution is provided, downloads the best resolution"
            "Runs the command line program ffmpeg to combine the audio and video"
        ),
    )

    return parser.parse_args(args)


def build_playback_report(youtube: YouTube) -> None:
    """Serialize the request data to json for offline debugging.

    :param YouTube youtube:
        A YouTube object.
    """
    ts = int(dt.datetime.utcnow().timestamp())
    fp = os.path.join(os.getcwd(), f"yt-video-{youtube.video_id}-{ts}.json.gz")

    js = youtube.js
    watch_html = youtube.watch_html
    vid_info = youtube.vid_info

    with gzip.open(fp, "wb") as fh:
        fh.write(
            json.dumps(
                {
                    "url": youtube.watch_url,
                    "js": js,
                    "watch_html": watch_html,
                    "video_info": vid_info,
                }
            ).encode("utf8"),
        )


def display_progress_bar(
    bytes_received: int, filesize: int, ch: str = "█", scale: float = 0.55
) -> None:
    """Display a simple, pretty progress bar.

    Example:
    ~~~~~~~~
    PSY - GANGNAM STYLE(강남스타일) MV.mp4
    ↳ |███████████████████████████████████████| 100.0%

    :param int bytes_received:
        The delta between the total file size (bytes) and bytes already
        written to disk.
    :param int filesize:
        File size of the media stream in bytes.
    :param str ch:
        Character to use for presenting progress segment.
    :param float scale:
        Scale multiplier to reduce progress bar size.

    """
    columns = shutil.get_terminal_size().columns
    max_width = int(columns * scale)

    filled = int(round(max_width * bytes_received / float(filesize)))
    remaining = max_width - filled
    progress_bar = ch * filled + " " * remaining
    percent = round(100.0 * bytes_received / float(filesize), 1)
    text = f" ↳ |{progress_bar}| {percent}%\r"
    sys.stdout.write(text)
    sys.stdout.flush()


# noinspection PyUnusedLocal
def on_progress(
    stream: Stream, chunk: bytes, bytes_remaining: int
) -> None:  # pylint: disable=W0613
    filesize = stream.filesize
    bytes_received = filesize - bytes_remaining
    display_progress_bar(bytes_received, filesize)


def _download(
    stream: Stream,
    target: Optional[str] = None,
    filename: Optional[str] = None,
) -> None:
    filesize_megabytes = stream.filesize // 1048576
    print(f"{filename or stream.default_filename} | {filesize_megabytes} MB")
    file_path = stream.get_file_path(filename=filename, output_path=target)
    if stream.exists_at_path(file_path):
        print(f"Already downloaded at:\n{file_path}")
        return

    stream.download(output_path=target, filename=filename)
    sys.stdout.write("\n")


def _unique_name(base: str, subtype: str, media_type: str, target: str) -> str:
    """
    Given a base name, the file format, and the target directory, will generate
    a filename unique for that directory and file format.
    :param str base:
        The given base-name.
    :param str subtype:
        The filetype of the video which will be downloaded.
    :param str media_type:
        The media_type of the file, ie. "audio" or "video"
    :param Path target:
        Target directory for download.
    """
    counter = 0
    while True:
        file_name = f"{base}_{media_type}_{counter}"
        file_path = os.path.join(target, f"{file_name}.{subtype}")
        if not os.path.exists(file_path):
            return file_name
        counter += 1


def ffmpeg_process(
    youtube: YouTube, resolution: str, target: Optional[str] = None
) -> None:
    """
    Decides the correct video stream to download, then calls _ffmpeg_downloader.

    :param YouTube youtube:
        A valid YouTube object.
    :param str resolution:
        YouTube video resolution.
    :param str target:
        Target directory for download
    """
    youtube.register_on_progress_callback(on_progress)
    target = target or os.getcwd()

    if resolution == "best":
        highest_quality_stream = (
            youtube.streams.filter(progressive=False)
            .order_by("resolution")
            .last()
        )
        mp4_stream = (
            youtube.streams.filter(progressive=False, subtype="mp4")
            .order_by("resolution")
            .last()
        )
        if highest_quality_stream.resolution == mp4_stream.resolution:
            video_stream = mp4_stream
        else:
            video_stream = highest_quality_stream
    else:
        video_stream = youtube.streams.filter(
            progressive=False, resolution=resolution, subtype="mp4"
        ).first()
        if not video_stream:
            video_stream = youtube.streams.filter(
                progressive=False, resolution=resolution
            ).first()
    if video_stream is None:
        print(f"Could not find a stream with resolution: {resolution}")
        print("Try one of these:")
        display_streams(youtube)
        sys.exit()

    audio_stream = youtube.streams.get_audio_only(video_stream.subtype)
    if not audio_stream:
        audio_stream = (
            youtube.streams.filter(only_audio=True).order_by("abr").last()
        )
    if not audio_stream:
        print("Could not find an audio only stream")
        sys.exit()
    _ffmpeg_downloader(
        audio_stream=audio_stream, video_stream=video_stream, target=target
    )


def _ffmpeg_downloader(
    audio_stream: Stream, video_stream: Stream, target: str
) -> None:
    """
    Given a YouTube Stream object, finds the correct audio stream, downloads them both
    giving them a unique name, them uses ffmpeg to create a new file with the audio
    and video from the previously downloaded files. Then deletes the original adaptive
    streams, leaving the combination.

    :param Stream audio_stream:
        A valid Stream object representing the audio to download
    :param Stream video_stream:
        A valid Stream object representing the video to download
    :param Path target:
        A valid Path object
    """
    video_unique_name = _unique_name(
        safe_filename(video_stream.title),
        video_stream.subtype,
        "video",
        target=target,
    )
    audio_unique_name = _unique_name(
        safe_filename(video_stream.title),
        audio_stream.subtype,
        "audio",
        target=target,
    )
    _download(stream=video_stream, target=target, filename=video_unique_name)
    print("Loading audio...")
    _download(stream=audio_stream, target=target, filename=audio_unique_name)

    video_path = os.path.join(
        target, f"{video_unique_name}.{video_stream.subtype}"
    )
    audio_path = os.path.join(
        target, f"{audio_unique_name}.{audio_stream.subtype}"
    )
    final_path = os.path.join(
        target, f"{safe_filename(video_stream.title)}.{video_stream.subtype}"
    )

    subprocess.run(  # nosec
        [
            "ffmpeg",
            "-i",
            video_path,
            "-i",
            audio_path,
            "-codec",
            "copy",
            final_path,
        ]
    )
    os.unlink(video_path)
    os.unlink(audio_path)


def download_by_itag(
    youtube: YouTube, itag: int, target: Optional[str] = None
) -> None:
    """Start downloading a YouTube video.

    :param YouTube youtube:
        A valid YouTube object.
    :param int itag:
        YouTube format identifier code.
    :param str target:
        Target directory for download
    """
    stream = youtube.streams.get_by_itag(itag)
    if stream is None:
        print(f"Could not find a stream with itag: {itag}")
        print("Try one of these:")
        display_streams(youtube)
        sys.exit()

    youtube.register_on_progress_callback(on_progress)

    try:
        _download(stream, target=target)
    except KeyboardInterrupt:
        sys.exit()


def download_by_resolution(
    youtube: YouTube, resolution: str, target: Optional[str] = None
) -> None:
    """Start downloading a YouTube video.

    :param YouTube youtube:
        A valid YouTube object.
    :param str resolution:
        YouTube video resolution.
    :param str target:
        Target directory for download
    """
    # TODO(nficano): allow dash itags to be selected
    stream = youtube.streams.get_by_resolution(resolution)
    if stream is None:
        print(f"Could not find a stream with resolution: {resolution}")
        print("Try one of these:")
        display_streams(youtube)
        sys.exit()

    youtube.register_on_progress_callback(on_progress)

    try:
        _download(stream, target=target)
    except KeyboardInterrupt:
        sys.exit()


def display_streams(youtube: YouTube) -> None:
    """Probe YouTube video and lists its available formats.

    :param YouTube youtube:
        A valid YouTube watch URL.

    """
    for stream in youtube.streams:
        print(stream)


def _print_available_captions(captions: CaptionQuery) -> None:
    print(
        f"Available caption codes are: {', '.join(c.code for c in captions)}"
    )


def download_caption(
    youtube: YouTube, lang_code: Optional[str], target: Optional[str] = None
) -> None:
    """Download a caption for the YouTube video.

    :param YouTube youtube:
        A valid YouTube object.
    :param str lang_code:
        Language code desired for caption file.
        Prints available codes if the value is None
        or the desired code is not available.
    :param str target:
        Target directory for download
    """
    if lang_code is None:
        _print_available_captions(youtube.captions)
        return

    try:
        caption = youtube.captions[lang_code]
        downloaded_path = caption.download(
            title=youtube.title, output_path=target
        )
        print(f"Saved caption file to: {downloaded_path}")
    except KeyError:
        print(f"Unable to find caption with code: {lang_code}")
        _print_available_captions(youtube.captions)


def download_audio(
    youtube: YouTube, filetype: str, target: Optional[str] = None
) -> None:
    """
    Given a filetype, downloads the highest quality available audio stream for a
    YouTube video.

    :param YouTube youtube:
        A valid YouTube object.
    :param str filetype:
        Desired file format to download.
    :param str target:
        Target directory for download
    """
    audio = (
        youtube.streams.filter(only_audio=True, subtype=filetype)
        .order_by("abr")
        .last()
    )

    if audio is None:
        print("No audio only stream found. Try one of these:")
        display_streams(youtube)
        sys.exit()

    youtube.register_on_progress_callback(on_progress)

    try:
        _download(audio, target=target)
    except KeyboardInterrupt:
        sys.exit()


if __name__ == "__main__":
    main()
