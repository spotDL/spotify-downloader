import os
import sys
from pathlib import Path
import signal

from spotdl.download import ffmpeg, DownloadManager
from spotdl.parsers import parse_arguments, parse_query
from spotdl.search import SpotifyClient


def console_entry_point():
    """
    This is where all the console processing magic happens.
    Its super simple, rudimentary even but, it's dead simple & it works.
    """

    # Parse arguments
    arguments = parse_arguments()

    # Convert arguments to dict
    args_dict = vars(arguments)

    if arguments.ffmpeg:
        args_dict["ffmpeg"] = str(Path(arguments.ffmpeg).absolute())
    else:
        args_dict["ffmpeg"] = "ffmpeg"

    # Check if ffmpeg has correct version, if not exit
    if (
        ffmpeg.has_correct_version(arguments.ignore_ffmpeg_version, args_dict["ffmpeg"])
        is False
    ):
        sys.exit(1)

    if "saved" in arguments.query and not arguments.user_auth:
        arguments.user_auth = True
        print(
            "Detected 'saved' in command line, but no --user-auth flag. Enabling Anyways."
        )
        print("Please Log In...")

    # Initialize spotify client
    SpotifyClient.init(
        client_id="5f573c9620494bae87890c0f08a60293",
        client_secret="212476d9b0f3472eaa762d90b19b0ba8",
        user_auth=arguments.user_auth,
    )

    # Change directory if user specified correct output path
    if arguments.output:
        if not os.path.isdir(arguments.output):
            sys.exit("The output directory doesn't exist.")
        print(f"Will download to: {os.path.abspath(arguments.output)}")
        os.chdir(arguments.output)

    # Start download manager
    with DownloadManager(args_dict) as downloader:
        if not arguments.debug_termination:

            def graceful_exit(signal, frame):
                downloader.display_manager.close()
                sys.exit(0)

            signal.signal(signal.SIGINT, graceful_exit)
            signal.signal(signal.SIGTERM, graceful_exit)

        # Find tracking files in queries
        tracking_files = [
            query for query in arguments.query if query.endswith(".spotdlTrackingFile")
        ]

        # Restart downloads
        for tracking_file in tracking_files:
            print("Preparing to resume download...")
            downloader.resume_download_from_tracking_file(tracking_file)

        # Get songs
        song_list = parse_query(
            arguments.query,
            arguments.output_format,
            arguments.use_youtube,
            arguments.generate_m3u,
            arguments.lyrics_provider,
            arguments.search_threads,
            arguments.path_template,
        )

        # Start downloading
        if len(song_list) > 0:
            downloader.download_multiple_songs(song_list)
