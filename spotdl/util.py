import os
import sys
import math
import urllib.request
import threading

import logging
logger = logging.getLogger(__name__)


try:
    import winreg
except ImportError:
    pass

try:
    from slugify import SLUG_OK, slugify
except ImportError:
    logger.error("Oops! `unicode-slugify` was not found.")
    logger.info("Please remove any other slugify library and install `unicode-slugify`")
    raise


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

    def join(self, *args, **kwargs):
        super().join(*args, **kwargs)
        return self._return


def merge_copy(base, overrider):
    return merge(base.copy(), overrider)

def merge(base, overrider):
    """ Override base dict with an overrider dict, recursively. """
    for key, value in overrider.items():
        if isinstance(value, dict):
            subitem = base.setdefault(key, {})
            merge(subitem, value)
        else:
            base[key] = value

    return base


def prompt_user_for_selection(items):
    """ Let the user input a choice. """
    logger.info("Enter a number:")
    while True:
        try:
            the_chosen_one = int(input("> "))
            if 1 <= the_chosen_one <= len(items):
                return items[the_chosen_one - 1]
            elif the_chosen_one == 0:
                return None
            else:
                logger.warning("Choose a valid number!")
        except ValueError:
            logger.warning("Choose a valid number!")


def is_spotify(track):
    """ Check if the input song is a Spotify link. """
    status = len(track) == 22 and track.replace(" ", "%20") == track
    status = status or track.find("spotify") > -1
    return status


def is_youtube(track):
    """ Check if the input song is a YouTube link. """
    status = len(track) == 11 and track.replace(" ", "%20") == track
    status = status and not track.lower() == track
    status = status or "youtube.com/watch?v=" in track
    return status


def track_type(track):
    track_types = {
        "spotify": is_spotify,
        "youtube": is_youtube,
    }
    for provider, fn in track_types.items():
        if fn(track):
            return provider
    return "query"


def sanitize(string, ok="&-_()[]{}", spaces_to_underscores=False):
    """ Generate filename of the song to be downloaded. """
    if spaces_to_underscores:
        string = string.replace(" ", "_")
    # replace slashes with "-" to avoid directory creation errors
    string = string.replace("/", "-").replace("\\", "-")
    # slugify removes any special characters
    string = slugify(string, ok=ok, lower=False, spaces=True)
    return string


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


def titlecase(string):
    return " ".join(word.capitalize() for word in string.split())


def readlines_from_nonbinary_file(path):
    with open(path, "r") as fin:
        lines = fin.read().splitlines()
    return lines


def writelines_to_nonbinary_file(path, lines):
    with open(path, "w") as fout:
        fout.writelines(map(lambda x: x + "\n", lines))

