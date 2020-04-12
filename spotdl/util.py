from logzero import logger as log
import os
import sys
import math
import urllib.request

import threading


try:
    import winreg
except ImportError:
    pass

try:
    from slugify import SLUG_OK, slugify
except ImportError:
    log.error("Oops! `unicode-slugify` was not found.")
    log.info("Please remove any other slugify library and install `unicode-slugify`")
    sys.exit(5)


# This has been referred from
# https://stackoverflow.com/a/6894023/6554943
# It's because threaded functions do not return by default
# Whereas this will return the value when `join` method
# is called.
class ThreadWithReturnValue(threading.Thread):
    def __init__(self, target=lambda: None, args=()):
        super().__init__(target=target, args=args)
        self._return = None
    def run(self):
        if self._target is not None:
            self._return = self._target(
                *self._args,
                **self._kwargs
            )
    def join(self, *args):
        super().join(*args)
        return self._return


def merge(base, overrider):
    """ Override default dict with config dict. """
    merger = base.copy()
    merger.update(overrider)
    return merger


def input_link(links):
    """ Let the user input a choice. """
    while True:
        try:
            log.info("Choose your number:")
            the_chosen_one = int(input("> "))
            if 1 <= the_chosen_one <= len(links):
                return links[the_chosen_one - 1]
            elif the_chosen_one == 0:
                return None
            else:
                log.warning("Choose a valid number!")
        except ValueError:
            log.warning("Choose a valid number!")


def is_spotify(raw_song):
    """ Check if the input song is a Spotify link. """
    status = len(raw_song) == 22 and raw_song.replace(" ", "%20") == raw_song
    status = status or raw_song.find("spotify") > -1
    return status


def is_youtube(raw_song):
    """ Check if the input song is a YouTube link. """
    status = len(raw_song) == 11 and raw_song.replace(" ", "%20") == raw_song
    status = status and not raw_song.lower() == raw_song
    status = status or "youtube.com/watch?v=" in raw_song
    return status


def format_string(string, metadata, output_extension=""):
    formats = {
        "{track-name}"   : metadata["name"],
        "{artist}"       : metadata["artists"][0]["name"],
        "{album}"        : metadata["album"]["name"],
        "{album-artist}" : metadata["artists"][0]["name"],
        "{genre}"        : metadata["genre"],
        "{disc-number}"  : metadata["disc_number"],
        "{duration}"     : metadata["duration"],
        "{year}"         : metadata["year"],
        "{original-date}": metadata["release_date"],
        "{track-number}" : metadata["track_number"],
        "{total-tracks}" : metadata["total_tracks"],
        "{isrc}"         : metadata["external_ids"]["isrc"],
        "{track-id}"     : metadata.get("id", ""),
        "{output-ext}"   : output_extension,
    }

    for key, value in formats.items():
        string = string.replace(key, str(value))

    return string


def sanitize_title(title, ok="-_()[]{}"):
    """ Generate filename of the song to be downloaded. """

    if const.args.no_spaces:
        title = title.replace(" ", "_")

    # replace slashes with "-" to avoid folder creation errors
    title = title.replace("/", "-").replace("\\", "-")

    # slugify removes any special characters
    title = slugify(title, ok=ok, lower=False, spaces=True)
    return title


def filter_path(path):
    if not os.path.exists(path):
        os.makedirs(path)
    for temp in os.listdir(path):
        if temp.endswith(".temp"):
            os.remove(os.path.join(path, temp))


def videotime_from_seconds(time):
    if time < 60:
        return str(time)
    if time < 3600:
        return "{0}:{1:02}".format(time // 60, time % 60)

    return "{0}:{1:02}:{2:02}".format((time // 60) // 60, (time // 60) % 60, time % 60)


def get_sec(time_str):
    if ":" in time_str:
        splitter = ":"
    elif "." in time_str:
        splitter = "."
    else:
        raise ValueError(
            "No expected character found in {} to split" "time values.".format(time_str)
        )
    v = time_str.split(splitter, 3)
    v.reverse()
    sec = 0
    if len(v) > 0:  # seconds
        sec += int(v[0])
    if len(v) > 1:  # minutes
        sec += int(v[1]) * 60
    if len(v) > 2:  # hours
        sec += int(v[2]) * 3600
    return sec


# a hacky way to get user's localized music directory
# (thanks @linusg, issue #203)
def get_music_dir():
    home = os.path.expanduser("~")

    # On Linux, the localized folder names are the actual ones.
    # It's a freedesktop standard though.
    if sys.platform.startswith("linux"):
        for file_item in (".config/user-dirs.dirs", "user-dirs.dirs"):
            path = os.path.join(home, file_item)
            if os.path.isfile(path):
                with open(path, "r") as f:
                    for line in f:
                        if line.startswith("XDG_MUSIC_DIR"):
                            return os.path.expandvars(
                                line.strip().split("=")[1].strip('"')
                            )

    # Windows / Cygwin
    # Queries registry for 'My Music' folder path (as this can be changed)
    if "win" in sys.platform:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
                0,
                winreg.KEY_ALL_ACCESS,
            )
            return winreg.QueryValueEx(key, "My Music")[0]
        except (FileNotFoundError, NameError):
            pass

    # On both Windows and macOS, the localized folder names you see in
    # Explorer and Finder are actually in English on the file system.
    # So, defaulting to C:\Users\<user>\Music or /Users/<user>/Music
    # respectively is sufficient.
    # On Linux, default to /home/<user>/Music if the above method failed.
    return os.path.join(home, "Music")


def remove_duplicates(elements, condition=lambda _: True, operation=lambda x: x):
    """
    Removes duplicates from a list whilst preserving order.

    We could directly call `set()` on the list but it changes
    the order of elements.
    """

    local_set = set()
    local_set_add = local_set.add
    filtered_list = []
    for x in elements:
        if condition(x) and not (x in local_set or local_set_add(x)):
            operated = operation(x)
            filtered_list.append(operated)
            local_set_add(operated)
    return filtered_list


def content_available(url):
    try:
        response = urllib.request.urlopen(url)
    except urllib.request.HTTPError:
        return False
    else:
        return response.getcode() < 300

