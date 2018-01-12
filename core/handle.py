import logging
import argparse
import os
import sys


_LOG_LEVELS_STR = ['INFO', 'WARNING', 'ERROR', 'DEBUG']

def log_leveller(log_level_str):
    loggin_levels = [logging.INFO, logging.WARNING, logging.ERROR, logging.DEBUG]
    log_level_str_index = _LOG_LEVELS_STR.index(log_level_str)
    loggin_level = loggin_levels[log_level_str_index]
    return loggin_level


def get_arguments(to_group=True, raw_args=None):
    parser = argparse.ArgumentParser(
        description='Download and convert songs from Spotify, Youtube etc.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    if to_group:
        group = parser.add_mutually_exclusive_group(required=True)

        group.add_argument(
            '-s', '--song', help='download song by spotify link or name')
        group.add_argument(
            '-l', '--list', help='download songs from a file')
        group.add_argument(
            '-p', '--playlist', help='load songs from playlist URL into <playlist_name>.txt')
        group.add_argument(
            '-b', '--album', help='load songs from album URL into <album_name>.txt')
        group.add_argument(
            '-u', '--username',
            help="load songs from user's playlist into <playlist_name>.txt")

    parser.add_argument(
        '-m', '--manual', default=False,
        help='choose the song to download manually', action='store_true')
    parser.add_argument(
        '-nm', '--no-metadata', default=False,
        help='do not embed metadata in songs', action='store_true')
    parser.add_argument(
        '-a', '--avconv', default=False,
        help='Use avconv for conversion otherwise set defaults to ffmpeg',
        action='store_true')
    parser.add_argument(
        '-f', '--folder', default=(os.path.join(sys.path[0], 'Music')),
        help='path to folder where files will be stored in')
    parser.add_argument(
        '--overwrite', default='prompt',
        help='change the overwrite policy',
        choices={'prompt', 'force', 'skip'})
    parser.add_argument(
        '-i', '--input-ext', default='.m4a',
        help='prefered input format .m4a or .webm (Opus)')
    parser.add_argument(
        '-o', '--output-ext', default='.mp3',
        help='prefered output extension .mp3 or .m4a (AAC)')
    parser.add_argument(
        '-dm', '--download-only-metadata', default=False,
        help='download songs for which metadata is found',
        action='store_true')
    parser.add_argument(
        '-d', '--dry-run', default=False,
        help='Show only track title and YouTube URL',
        action='store_true')
    parser.add_argument(
        '-mo', '--music-videos-only', default=False,
        help='Search only for music on Youtube',
        action='store_true')
    parser.add_argument(
        '-ll', '--log-level', default='INFO',
        choices=_LOG_LEVELS_STR,
        type=str.upper,
        help='set log verbosity')

    parsed = parser.parse_args(raw_args)
    parsed.log_level = log_leveller(parsed.log_level)

    return parsed
