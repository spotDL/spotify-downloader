import os
import sys

from core import const

log = const.log

try:
    from slugify import SLUG_OK, slugify
except ImportError:
    log.error('Oops! `unicode-slugify` was not found.')
    log.info('Please remove any other slugify library and install `unicode-slugify`')
    sys.exit(5)

formats = { 0  : 'track_name',
            1  : 'artist',
            2  : 'album',
            3  : 'album_artist',
            4  : 'genre',
            5  : 'disc_number',
            6  : 'duration',
            7  : 'year',
            8  : 'original_date',
            9  : 'track_number',
            10 : 'total_tracks',
            11 : 'isrc' }


def input_link(links):
    """ Let the user input a choice. """
    while True:
        try:
            log.info('Choose your number:')
            the_chosen_one = int(input('> '))
            if 1 <= the_chosen_one <= len(links):
                return links[the_chosen_one - 1]
            elif the_chosen_one == 0:
                return None
            else:
                log.warning('Choose a valid number!')
        except ValueError:
            log.warning('Choose a valid number!')


def trim_song(text_file):
    """ Remove the first song from file. """
    with open(text_file, 'r') as file_in:
        data = file_in.read().splitlines(True)
    with open(text_file, 'w') as file_out:
        file_out.writelines(data[1:])
    return data[0]


def is_spotify(raw_song):
    """ Check if the input song is a Spotify link. """
    status = len(raw_song) == 22 and raw_song.replace(" ", "%20") == raw_song
    status = status or raw_song.find('spotify') > -1
    return status


def is_youtube(raw_song):
    """ Check if the input song is a YouTube link. """
    status = len(raw_song) == 11 and raw_song.replace(" ", "%20") == raw_song
    status = status and not raw_song.lower() == raw_song
    status = status or 'youtube.com/watch?v=' in raw_song
    return status


def format_string(string_format, tags):
    """ Generate a string of the format '[artist] - [song]' for the given spotify song. """
    format_tags = dict(formats)
    format_tags[0]  = tags['name']
    format_tags[1]  = tags['artists'][0]['name']
    format_tags[2]  = tags['album']['name']
    format_tags[3]  = tags['artists'][0]['name']
    format_tags[4]  = tags['genre']
    format_tags[5]  = tags['disc_number']
    format_tags[6]  = tags['duration']
    format_tags[7]  = tags['year']
    format_tags[8]  = tags['release_date']
    format_tags[9]  = tags['track_number']
    format_tags[10] = tags['total_tracks']
    format_tags[11] = tags['external_ids']['isrc']

    for x in formats:
        string_format = string_format.replace('{' + formats[x] + '}',
                                          str(format_tags[x]))

    if const.args.no_spaces:
        string_format = string_format.replace(' ', '_')

    return string_format


def sanitize_title(title):
    """ Generate filename of the song to be downloaded. """

    if const.args.no_spaces:
        title = title.replace(' ', '_')

    # slugify removes any special characters
    title = slugify(title, ok='-_()[]{}\/', lower=False, spaces=True)
    return title


def filter_path(path):
    if not os.path.exists(path):
        os.makedirs(path)
    for temp in os.listdir(path):
        if temp.endswith('.temp'):
            os.remove(os.path.join(path, temp))


def videotime_from_seconds(time):
    if time < 60:
        return str(time)
    if time < 3600:
        return '{0}:{1:02}'.format(time//60, time % 60)

    return '{0}:{1:02}:{2:02}'.format((time//60)//60, (time//60) % 60, time % 60)


def get_sec(time_str):
    v = time_str.split(':', 3)
    v.reverse()
    sec = 0
    if len(v) > 0:  # seconds
        sec += int(v[0])
    if len(v) > 1:  # minutes
        sec += int(v[1]) * 60
    if len(v) > 2:  # hours
        sec += int(v[2]) * 3600
    return sec


def get_splits(url):
    if '/' in url:
        if url.endswith('/'):
            url = url[:-1]
        splits = url.split('/')
    else:
        splits = url.split(':')
    return splits
