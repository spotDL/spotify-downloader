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
from logzero import logger as log
from slugify import slugify
import spotipy
import urllib.request
import logzero
import os
import sys
import time
import platform
import pprint


def check_exists(music_file, raw_song, meta_tags):
    """ Check if the input song already exists in the given folder. """
    log.debug(
        "Cleaning any temp files and checking "
        'if "{}" already exists'.format(music_file)
    )
    songs = os.listdir(const.args.folder)
    for song in songs:
        if song.endswith(".temp"):
            os.remove(os.path.join(const.args.folder, song))
            continue
        # check if a song with the same name is already present in the given folder
        if os.path.splitext(song)[0] == music_file:
            log.debug('Found an already existing song: "{}"'.format(song))
            if internals.is_spotify(raw_song):
                # check if the already downloaded song has correct metadata
                # if not, remove it and download again without prompt
                already_tagged = metadata.compare(
                    os.path.join(const.args.folder, song), meta_tags
                )
                log.debug(
                    "Checking if it is already tagged correctly? {}", already_tagged
                )
                if not already_tagged:
                    os.remove(os.path.join(const.args.folder, song))
                    return False

            log.warning('"{}" already exists'.format(song))
            if const.args.overwrite == "prompt":
                log.info(
                    '"{}" has already been downloaded. '
                    "Re-download? (y/N): ".format(song)
                )
                prompt = input("> ")
                if prompt.lower() == "y":
                    os.remove(os.path.join(const.args.folder, song))
                    return False
                else:
                    return True
            elif const.args.overwrite == "force":
                os.remove(os.path.join(const.args.folder, song))
                log.info('Overwriting "{}"'.format(song))
                return False
            elif const.args.overwrite == "skip":
                log.info('Skipping "{}"'.format(song))
                return True
    return False


class Downloader:
    def __init__(self, raw_song, number=None):
        self.raw_song = raw_song
        self.number = number
        self.content, self.meta_tags = youtube_tools.match_video_and_metadata(raw_song)

    def download_single(self):
        """ Logic behind downloading a song. """

        if self._to_skip():
            return

        # "[number]. [artist] - [song]" if downloading from list
        # otherwise "[artist] - [song]"
        youtube_title = youtube_tools.get_youtube_title(self.content, self.number)
        log.info("{} ({})".format(youtube_title, self.content.watchv_url))

        # generate file name of the song to download
        songname = self.refine_songname(self.content.title)

        if const.args.dry_run:
            return

        if not check_exists(songname, self.raw_song, self.meta_tags):
            return self._download_single(songname)

    def _download_single(self, songname):
        # deal with file formats containing slashes to non-existent directories
        songpath = os.path.join(const.args.folder, os.path.dirname(songname))
        os.makedirs(songpath, exist_ok=True)
        input_song = songname + const.args.input_ext
        output_song = songname + const.args.output_ext
        if youtube_tools.download_song(input_song, self.content):
            print("")
            try:
                convert.song(
                    input_song,
                    output_song,
                    const.args.folder,
                    avconv=const.args.avconv,
                    trim_silence=const.args.trim_silence,
                )
            except FileNotFoundError:
                output_song = self.unconverted_filename(songname)

            if not const.args.input_ext == const.args.output_ext:
                os.remove(os.path.join(const.args.folder, input_song))
            if not const.args.no_metadata and self.meta_tags is not None:
                metadata.embed(
                    os.path.join(const.args.folder, output_song), self.meta_tags
                )
            return True

    def _to_skip(self):
        if self.content is None:
            log.debug("Found no matching video")
            return True

        if const.args.download_only_metadata and self.meta_tags is None:
            log.info("Found no metadata. Skipping the download")
            return True

    def refine_songname(self, songname):
        if self.meta_tags is not None:
            refined_songname = internals.format_string(
                const.args.file_format, self.meta_tags, slugification=True
            )
            log.debug(
                'Refining songname from "{0}" to "{1}"'.format(
                    songname, refined_songname
                )
            )
            if not refined_songname == " - ":
                songname = refined_songname
        else:
            if not const.args.no_metadata:
                log.warning("Could not find metadata")
            songname = internals.sanitize_title(songname)

        return songname

    @staticmethod
    def unconverted_filename(songname):
        encoder = "avconv" if const.args.avconv else "ffmpeg"
        log.warning("Could not find {0}, skipping conversion".format(encoder))
        const.args.output_ext = const.args.input_ext
        output_song = songname + const.args.output_ext
        return output_song


class ListDownloader:
    def __init__(self, tracks_file, skip_file=None, write_successful_file=None):
        self.tracks_file = tracks_file
        self.skip_file = skip_file
        self.write_successful_file = write_successful_file
        self.tracks = internals.get_unique_tracks(self.tracks_file)

    def download_list(self):
        """ Download all songs from the list. """
        # override file with unique tracks
        log.info("Overriding {} with unique tracks".format(self.tracks_file))
        self._override_file()

        # Remove tracks to skip from tracks list
        if self.skip_file is not None:
            self.tracks = self._filter_tracks_against_skip_file()

        log.info(u"Preparing to download {} songs".format(len(self.tracks)))
        return self._download_list()

    def _download_list(self):
        downloaded_songs = []

        for number, raw_song in enumerate(self.tracks, 1):
            print("")
            try:
                track_dl = Downloader(raw_song, number=number)
                track_dl.download_single()
            except spotipy.client.SpotifyException:
                # token expires after 1 hour
                self._regenerate_token()
                track_dl.download_single()
            # detect network problems
            except (urllib.request.URLError, TypeError, IOError) as e:
                self._cleanup(raw_song, e)
                # TODO: remove this sleep once #397 is fixed
                # wait 0.5 sec to avoid infinite looping
                time.sleep(0.5)
                continue

            downloaded_songs.append(raw_song)
            # Add track to file of successful downloads
            if self.write_successful_file is not None:
                self._write_successful(raw_song)

            log.debug("Removing downloaded song from tracks file")
            internals.trim_song(self.tracks_file)

        return downloaded_songs

    def _override_file(self):
        with open(self.tracks_file, "w") as f:
            f.write("\n".join(self.tracks))

    def _write_successful(self, raw_song):
        log.debug("Adding downloaded song to write successful file")
        with open(self.write_successful_file, "a") as f:
            f.write("\n" + raw_song)

    @staticmethod
    def _regenerate_token():
        log.debug("Token expired, generating new one and authorizing")
        spotify_tools.refresh_token()

    def _cleanup(self, raw_song, exception):
        self.tracks.append(raw_song)
        # remove the downloaded song from file
        internals.trim_song(self.tracks_file)
        # and append it at the end of file
        with open(self.tracks_file, "a") as f:
            f.write("\n" + raw_song)
        log.exception(exception)
        log.warning("Failed to download song. Will retry after other songs\n")

    def _filter_tracks_against_skip_file(self):
        skip_tracks = internals.get_unique_tracks(self.skip_file)
        len_before = len(self.tracks)
        tracks = [track for track in self.tracks if track not in skip_tracks]
        log.info("Skipping {} tracks".format(len_before - len(tracks)))
        return tracks


def main():
    const.args = handle.get_arguments()

    if const.args.version:
        print("spotdl {version}".format(version=__version__))
        sys.exit()

    internals.filter_path(const.args.folder)
    youtube_tools.set_api_key()

    logzero.setup_default_logger(formatter=const._formatter, level=const.args.log_level)

    log.debug("Python version: {}".format(sys.version))
    log.debug("Platform: {}".format(platform.platform()))
    log.debug(pprint.pformat(const.args.__dict__))

    try:
        if const.args.song:
            track_dl = Downloader(raw_song=const.args.song)
            track_dl.download_single()
        elif const.args.list:
            if const.args.write_m3u:
                youtube_tools.generate_m3u(track_file=const.args.list)
            else:
                list_dl = ListDownloader(
                    tracks_file=const.args.list,
                    skip_file=const.args.skip,
                    write_successful_file=const.args.write_successful,
                )
                list_dl.download_list()
        elif const.args.playlist:
            spotify_tools.write_playlist(playlist_url=const.args.playlist)
        elif const.args.album:
            spotify_tools.write_album(album_url=const.args.album)
        elif const.args.all_albums:
            spotify_tools.write_all_albums_from_artist(artist_url=const.args.all_albums)
        elif const.args.username:
            spotify_tools.write_user_playlist(username=const.args.username)

        # actually we don't necessarily need this, but yeah...
        # explicit is better than implicit!
        sys.exit(0)

    except KeyboardInterrupt as e:
        log.exception(e)
        sys.exit(3)


if __name__ == "__main__":
    main()
