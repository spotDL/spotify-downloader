#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
from spotdl import __version__
from spotdl import const
from spotdl import handle
from spotdl import metadata
from spotdl import convert
from spotdl import internals
from spotdl import spotify_tools
from spotdl import youtube_tools
from slugify import slugify
import spotipy
import urllib.request
import os
import sys
import time
import platform
import pprint


def check_exists(music_file, raw_song, meta_tags):
    """ Check if the input song already exists in the given folder. """
    log.debug('Cleaning any temp files and checking '
              'if "{}" already exists'.format(music_file))
    songs = os.listdir(const.args.folder)
    for song in songs:
        if song.endswith('.temp'):
            os.remove(os.path.join(const.args.folder, song))
            continue
        # check if a song with the same name is already present in the given folder
        if os.path.splitext(song)[0] == music_file:
            log.debug('Found an already existing song: "{}"'.format(song))
            if internals.is_spotify(raw_song):
                # check if the already downloaded song has correct metadata
                # if not, remove it and download again without prompt
                already_tagged = metadata.compare(os.path.join(const.args.folder, song),
                                                  meta_tags)
                log.debug('Checking if it is already tagged correctly? {}',
                                                            already_tagged)
                if not already_tagged:
                    os.remove(os.path.join(const.args.folder, song))
                    return False

            log.warning('"{}" already exists'.format(song))
            if const.args.overwrite == 'prompt':
                log.info('"{}" has already been downloaded. '
                         'Re-download? (y/N): '.format(song))
                prompt = input('> ')
                if prompt.lower() == 'y':
                    os.remove(os.path.join(const.args.folder, song))
                    return False
                else:
                    return True
            elif const.args.overwrite == 'force':
                os.remove(os.path.join(const.args.folder, song))
                log.info('Overwriting "{}"'.format(song))
                return False
            elif const.args.overwrite == 'skip':
                log.info('Skipping "{}"'.format(song))
                return True
    return False


def download_list(text_file):
    """ Download all songs from the list. """
    with open(text_file, 'r') as listed:
        # read tracks into a list and remove any duplicates
        lines = listed.read().splitlines()
        lines = list(set(lines))
    # ignore blank lines in text_file (if any)
    try:
        lines.remove('')
    except ValueError:
        pass

    log.info(u'Preparing to download {} songs'.format(len(lines)))
    downloaded_songs = []

    for number, raw_song in enumerate(lines, 1):
        print('')
        try:
            download_single(raw_song, number=number)
        # token expires after 1 hour
        except spotipy.client.SpotifyException:
            # refresh token when it expires
            log.debug('Token expired, generating new one and authorizing')
            new_token = spotify_tools.generate_token()
            spotify_tools.spotify = spotipy.Spotify(auth=new_token)
            download_single(raw_song, number=number)
        # detect network problems
        except (urllib.request.URLError, TypeError, IOError):
            lines.append(raw_song)
            # remove the downloaded song from file
            internals.trim_song(text_file)
            # and append it at the end of file
            with open(text_file, 'a') as myfile:
                myfile.write(raw_song + '\n')
            log.warning('Failed to download song. Will retry after other songs\n')
            # wait 0.5 sec to avoid infinite looping
            time.sleep(0.5)
            continue

        downloaded_songs.append(raw_song)
        log.debug('Removing downloaded song from text file')
        internals.trim_song(text_file)

    return downloaded_songs


def download_single(raw_song, number=None):
    """ Logic behind downloading a song. """
    if internals.is_youtube(raw_song):
        log.debug('Input song is a YouTube URL')
        content = youtube_tools.go_pafy(raw_song, meta_tags=None)
        raw_song = slugify(content.title).replace('-', ' ')
        meta_tags = spotify_tools.generate_metadata(raw_song)
    else:
        meta_tags = spotify_tools.generate_metadata(raw_song)
        content = youtube_tools.go_pafy(raw_song, meta_tags)

    if content is None:
        log.debug('Found no matching video')
        return

    if const.args.download_only_metadata and meta_tags is None:
        log.info('Found no metadata. Skipping the download')
        return

    # "[number]. [artist] - [song]" if downloading from list
    # otherwise "[artist] - [song]"
    youtube_title = youtube_tools.get_youtube_title(content, number)
    log.info('{} ({})'.format(youtube_title, content.watchv_url))

    # generate file name of the song to download
    songname = content.title

    if meta_tags is not None:
        refined_songname = internals.format_string(const.args.file_format,
                                                   meta_tags,
                                                   slugification=True)
        log.debug('Refining songname from "{0}" to "{1}"'.format(songname, refined_songname))
        if not refined_songname == ' - ':
            songname = refined_songname
    else:
        log.warning('Could not find metadata')
        songname = internals.sanitize_title(songname)

    if const.args.dry_run:
        return

    if not check_exists(songname, raw_song, meta_tags):
        # deal with file formats containing slashes to non-existent directories
        songpath = os.path.join(const.args.folder, os.path.dirname(songname))
        os.makedirs(songpath, exist_ok=True)
        input_song = songname + const.args.input_ext
        output_song = songname + const.args.output_ext
        if youtube_tools.download_song(input_song, content):
            print('')
            try:
                convert.song(input_song, output_song, const.args.folder,
                             avconv=const.args.avconv, trim_silence=const.args.trim_silence)
            except FileNotFoundError:
                encoder = 'avconv' if const.args.avconv else 'ffmpeg'
                log.warning('Could not find {0}, skipping conversion'.format(encoder))
                const.args.output_ext = const.args.input_ext
                output_song = songname + const.args.output_ext

            if not const.args.input_ext == const.args.output_ext:
                os.remove(os.path.join(const.args.folder, input_song))
            if not const.args.no_metadata and meta_tags is not None:
                metadata.embed(os.path.join(const.args.folder, output_song), meta_tags)
            return True


def main():
    const.args = handle.get_arguments()

    if const.args.version:
        print('spotdl {version}'.format(version=__version__))
        sys.exit()

    internals.filter_path(const.args.folder)
    youtube_tools.set_api_key()

    const.log = const.logzero.setup_logger(formatter=const._formatter,
                                      level=const.args.log_level)
    global log
    log = const.log
    log.debug('Python version: {}'.format(sys.version))
    log.debug('Platform: {}'.format(platform.platform()))
    log.debug(pprint.pformat(const.args.__dict__))

    try:
        if const.args.song:
            download_single(raw_song=const.args.song)
        elif const.args.list:
            download_list(text_file=const.args.list)
        elif const.args.playlist:
            spotify_tools.write_playlist(playlist_url=const.args.playlist)
        elif const.args.album:
            spotify_tools.write_album(album_url=const.args.album)
        elif const.args.username:
            spotify_tools.write_user_playlist(username=const.args.username)

        # actually we don't necessarily need this, but yeah...
        # explicit is better than implicit!
        sys.exit(0)

    except KeyboardInterrupt as e:
        log.exception(e)
        sys.exit(3)


if __name__ == '__main__':
    main()
