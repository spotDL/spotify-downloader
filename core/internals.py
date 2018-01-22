from slugify import SLUG_OK, slugify
from core import const

try:
    from slugify import SLUG_OK, slugify
except ImportError:
    log.warning('Remove any other slugifies and install unicode-slugify')

import os

log = const.log

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


def generate_songname(file_format, tags):
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
        file_format = file_format.replace('{' + formats[x] + '}',
                                          str(format_tags[x]))

    if const.args.no_spaces:
        file_format = file_format.replace(' ', '_')

    return file_format


def sanitize_title(title):
    """ Generate filename of the song to be downloaded. """
    # slugify removes any special characters
    title = slugify(title, ok='-_()[]{}\/', lower=False,
                    spaces=(not const.args.no_spaces))
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
        return '{}:{}'.format(str(time // 60), str(time % 60).zfill(2))

    return '{}:{}:{}'.format(str(time // 60),
                             str((time % 60) // 60).zfill(2),
                             str((time % 60) % 60).zfill(2))
