import sys
import os
import argparse
import spotipy.oauth2 as oauth2
from urllib.request import quote
from slugify import slugify


def input_link(links):
    """Let the user input a number."""
    while True:
        try:
            the_chosen_one = int(input('>> Choose your number: '))
            if 1 <= the_chosen_one <= len(links):
                return links[the_chosen_one - 1]
            elif the_chosen_one == 0:
                return None
            else:
                print('Choose a valid number!')
        except ValueError:
            print('Choose a valid number!')


def trim_song(file):
    """Remove the first song from file."""
    with open(file, 'r') as file_in:
        data = file_in.read().splitlines(True)
    with open(file, 'w') as file_out:
        file_out.writelines(data[1:])


def get_arguments():
    parser = argparse.ArgumentParser(
        description='Download and convert songs from Spotify, Youtube etc.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        '-s', '--song', help='download song by spotify link or name')
    group.add_argument(
        '-l', '--list', help='download songs from a file')
    group.add_argument(
        '-p', '--playlist', help='load songs from playlist URL into <playlist_name>.txt')
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
        '-f', '--folder', default='Music/',
        help='path to folder where files will be stored in')
    parser.add_argument(
        '-v', '--verbose', default=False, help='show debug output',
        action='store_true')
    parser.add_argument(
        '-i', '--input_ext', default='.m4a',
        help='prefered input format .m4a or .webm (Opus)')
    parser.add_argument(
        '-o', '--output_ext', default='.mp3',
        help='prefered output extension .mp3 or .m4a (AAC)')

    return parser.parse_args()


def is_spotify(raw_song):
    """Check if the input song is a Spotify link."""
    if (len(raw_song) == 22 and raw_song.replace(" ", "%20") == raw_song) or \
            (raw_song.find('spotify') > -1):
        return True
    else:
        return False


def sanitize_title(title):
    """Generate filename of the song to be downloaded."""
    title = title.replace(' ', '_')
    title = title.replace('/', '_')

    # slugify removes any special characters
    title = slugify(title, ok='-_()[]{}', lower=False)
    return title


def generate_token():
    """Generate the token. Please respect these credentials :)"""
    credentials = oauth2.SpotifyClientCredentials(
        client_id='4fe3fecfe5334023a1472516cc99d805',
        client_secret='0f02b7c483c04257984695007a4a8d5c')
    token = credentials.get_access_token()
    return token


def generate_search_url(song, viewsort=False):
    """Generate YouTube search URL for the given song."""
    # urllib.request.quote() encodes URL with special characters
    song = quote(song)
    if viewsort:
        url = u"https://www.youtube.com/results?q={0}".format(song)
    else:
        url = u"https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q={0}".format(song)

    return url


def filter_path(path):
    os.chdir(sys.path[0])
    if not os.path.exists(path):
        os.makedirs(path)
    for temp in os.listdir(path):
        if temp.endswith('.temp'):
            os.remove(os.path.join(path, temp))


def grace_quit():
    print('\n\nExiting.')
    sys.exit()

def get_sec(time_str):
   v = time_str.split(':', 3)
   v.reverse()
   sec = 0
   if len(v) > 0: #seconds
       sec += int(v[0])
   if len(v) > 1: # minutes
       sec += int(v[1]) * 60
   if len(v) > 2: # hours
       sec += int(v[2]) * 3600
   return sec
