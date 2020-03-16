from logzero import logger as log
import os
import sys
import math
import urllib.request


from spotdl import const

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

formats = {
    0: "track_name",
    1: "artist",
    2: "album",
    3: "album_artist",
    4: "genre",
    5: "disc_number",
    6: "duration",
    7: "year",
    8: "original_date",
    9: "track_number",
    10: "total_tracks",
    11: "isrc",
    12: "track_id",
}


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


def trim_song(tracks_file):
    """ Remove the first song from file. """
    with open(tracks_file, "r") as file_in:
        data = file_in.read().splitlines(True)
    with open(tracks_file, "w") as file_out:
        file_out.writelines(data[1:])
    return data[0]


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


def format_string(
    string_format, tags, slugification=False, force_spaces=False, total_songs=0
):
    """ Generate a string of the format '[artist] - [song]' for the given spotify song. """
    format_tags = dict(formats)
    format_tags[0] = tags["name"]
    format_tags[1] = tags["artists"][0]["name"]
    format_tags[2] = tags["album"]["name"]
    format_tags[3] = tags["artists"][0]["name"]
    format_tags[4] = tags["genre"]
    format_tags[5] = tags["disc_number"]
    format_tags[6] = tags["duration"]
    format_tags[7] = tags["year"]
    format_tags[8] = tags["release_date"]
    format_tags[9] = tags["track_number"]
    format_tags[10] = tags["total_tracks"]
    format_tags[11] = tags["external_ids"]["isrc"]
    try:
        format_tags[12] = tags["id"]
    except KeyError:
        pass

    format_tags_sanitized = {
        k: sanitize_title(str(v), ok="'-_()[]{}") if slugification else str(v)
        for k, v in format_tags.items()
    }
    # calculating total digits presnet in total_songs to prepare a zfill.
    total_digits = 0 if total_songs == 0 else int(math.log10(total_songs)) + 1

    for x in formats:
        format_tag = "{" + formats[x] + "}"
        # Making consistent track number by prepending zero
        # on it according to number of digits in total songs
        if format_tag == "{track_number}":
            format_tags_sanitized[x] = format_tags_sanitized[x].zfill(total_digits)

        string_format = string_format.replace(format_tag, format_tags_sanitized[x])

    if const.args.no_spaces and not force_spaces:
        string_format = string_format.replace(" ", "_")

    return string_format


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


def extract_spotify_id(raw_string):
    """
    Returns a Spotify ID of a playlist, album, etc. after extracting
    it from a given HTTP URL or Spotify URI.
    """

    if "/" in raw_string:
        # Input string is an HTTP URL
        if raw_string.endswith("/"):
            raw_string = raw_string[:-1]
        # We need to manually trim additional text from HTTP URLs
        # We could skip this if https://github.com/plamere/spotipy/pull/324
        # gets merged,
        to_trim = raw_string.find("?")
        if not to_trim == -1:
            raw_string = raw_string[:to_trim]
        splits = raw_string.split("/")
    else:
        # Input string is a Spotify URI
        splits = raw_string.split(":")

    spotify_id = splits[-1]

    return spotify_id


def get_unique_tracks(tracks_file):
    """
    Returns a list of unique tracks given a path to a
    file containing tracks.
    """

    log.info(
        "Checking and removing any duplicate tracks "
        "in reading {}".format(tracks_file)
    )
    with open(tracks_file, "r") as tracks_in:
        # Read tracks into a list and remove any duplicates
        lines = tracks_in.read().splitlines()

    # Remove blank and strip whitespaces from lines (if any)
    lines = [line.strip() for line in lines if line.strip()]
    lines = remove_duplicates(lines)
    return lines


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


def remove_duplicates(tracks):
    """
    Removes duplicates from a list whilst preserving order.

    We could directly call `set()` on the list but it changes
    the order of elements.
    """

    local_set = set()
    local_set_add = local_set.add
    return [x for x in tracks if not (x in local_set or local_set_add(x))]


def content_available(url):
    try:
        response = urllib.request.urlopen(url)
    except urllib.request.HTTPError:
        return False
    else:
        return response.getcode() < 300
