#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from core import const
from core import handle
from core import metadata
from core import convert
from core import internals
from core import spotify_tools
from core import youtube_tools
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
        # check if any song with similar name is already present in the given folder
        file_name = internals.sanitize_title(music_file)
        if song.startswith(file_name):
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


def grab_list(text_file):
    """ Download all songs from the list. """
    with open(text_file, 'r') as listed:
        lines = (listed.read()).splitlines()
    # ignore blank lines in text_file (if any)
    try:
        lines.remove('')
    except ValueError:
        pass
    log.info(u'Preparing to download {} songs'.format(len(lines)))
    number = 1

    for raw_song in lines:
        print('')
        try:
            grab_single(raw_song, number=number)
        # token expires after 1 hour
        except spotipy.client.SpotifyException:
            # refresh token when it expires
            log.debug('Token expired, generating new one and authorizing')
            new_token = spotify_tools.generate_token()
            spotify_tools.spotify = spotipy.Spotify(auth=new_token)
            grab_single(raw_song, number=number)
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

        log.debug('Removing downloaded song from text file')
        internals.trim_song(text_file)
        number += 1


def grab_playlist(playlist):
    if '/' in playlist:
        if playlist.endswith('/'):
            playlist = playlist[:-1]
        splits = playlist.split('/')
    else:
        splits = playlist.split(':')

    try:
        username = splits[-3]
    except IndexError:
        # Wrong format, in either case
        log.error('The provided playlist URL is not in a recognized format!')
        sys.exit(10)
    playlist_id = splits[-1]
    try:
        spotify_tools.write_playlist(username, playlist_id)
    except spotipy.client.SpotifyException:
        log.error('Unable to find playlist')
        log.info('Make sure the playlist is set to publicly visible and then try again')
        sys.exit(11)


def grab_single(raw_song, number=None):
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
        refined_songname = internals.generate_songname(meta_tags)
        log.debug('Refining songname from "{0}" to "{1}"'.format(songname, refined_songname))
        if not refined_songname == ' - ':
            songname = refined_songname
    else:
        log.warning('Could not find metadata')


    if const.args.dry_run:
        return

    file_name = internals.sanitize_title(songname)

    if not check_exists(file_name, raw_song, meta_tags):
        if youtube_tools.download_song(file_name, content):
            input_song = file_name + const.args.input_ext
            output_song = file_name + const.args.output_ext
            print('')

            try:
                convert.song(input_song, output_song, const.args.folder,
                             avconv=const.args.avconv)
            except FileNotFoundError:
                encoder = 'avconv' if const.args.avconv else 'ffmpeg'
                log.warning('Could not find {0}, skipping conversion'.format(encoder))
                const.args.output_ext = const.args.input_ext
                output_song = file_name + const.args.output_ext

            if not const.args.input_ext == const.args.output_ext:
                os.remove(os.path.join(const.args.folder, input_song))

            if not const.args.no_metadata and meta_tags is not None:
                metadata.embed(os.path.join(const.args.folder, output_song), meta_tags)

        else:
            log.error('No audio streams available')


# token is mandatory when using Spotify's API
# https://developer.spotify.com/news-stories/2017/01/27/removing-unauthenticated-calls-to-the-web-api/
token = spotify_tools.generate_token()
spotify = spotipy.Spotify(auth=token)

if __name__ == '__main__':
    const.args = handle.get_arguments()
    internals.filter_path(const.args.folder)

    const.log = const.logzero.setup_logger(formatter=const.formatter,
                                      level=const.args.log_level)
    log = const.log
    log.debug('Python version: {}'.format(sys.version))
    log.debug('Platform: {}'.format(platform.platform()))
    log.debug(pprint.pformat(const.args.__dict__))

    try:
        if const.args.song:
            grab_single(raw_song=const.args.song)
        elif const.args.list:
            grab_list(text_file=const.args.list)
        elif const.args.playlist:
            grab_playlist(playlist=const.args.playlist)
        elif const.args.album:
            spotify_tools.grab_album(album=const.args.album)
        elif const.args.username:
            spotify_tools.feed_playlist(username=const.args.username)

        # actually we don't necessarily need this, but yeah...
        # explicit is better than implicit!
        sys.exit(0)

    except KeyboardInterrupt as e:
        log.exception(e)
        sys.exit(3)
