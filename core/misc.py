import argparse
import sys
import os
from slugify import slugify
import spotipy.oauth2 as oauth2

try:
    from urllib2 import quote
except:
    from urllib.request import quote

# method to input (user playlists) and (track when using manual mode)
def input_link(links):
    while True:
        try:
            the_chosen_one = int(user_input('>> Choose your number: '))
            if the_chosen_one >= 1 and the_chosen_one <= len(links):
                return links[the_chosen_one - 1]
            elif the_chosen_one == 0:
                return None
            else:
                print('Choose a valid number!')
        except ValueError:
            print('Choose a valid number!')

def user_input(string=''):
    if sys.version_info > (3, 0):
        return input(string)
    else:
        return raw_input(string)

# remove first song from .txt
def trim_song(file):
    with open(file, 'r') as fin:
        data = fin.read().splitlines(True)
    with open(file, 'w') as fout:
        fout.writelines(data[1:])

def get_arguments():
    parser = argparse.ArgumentParser(description='Download and convert songs \
                    from Spotify, Youtube etc.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('-s', '--song',
                        help='download song by spotify link or name')
    group.add_argument('-l', '--list',
                        help='download songs from a file')
    group.add_argument('-u', '--username',
                        help="load user's playlists into <playlist_name>.txt")
    parser.add_argument('-m', '--manual', default=False,
                        help='choose the song to download manually', action='store_true')
    parser.add_argument('-nm', '--no-metadata', default=False,
                        help='do not embed metadata in songs', action='store_true')
    parser.add_argument('-a', '--avconv', default=False,
                        help='Use avconv for conversion otherwise set defaults to ffmpeg',
                        action='store_true')
    parser.add_argument('-v', '--verbose', default=False,
                        help='show debug output', action='store_true')
    parser.add_argument('-i', '--input_ext', default='.m4a',
                        help='prefered input format .m4a or .webm (Opus)')
    parser.add_argument('-o', '--output_ext', default='.mp3',
                        help='prefered output extension .mp3 or .m4a (AAC)')

    return parser.parse_args()

# check if input song is spotify link
def is_spotify(raw_song):
    if (len(raw_song) == 22 and raw_song.replace(" ", "%20") == raw_song) or (raw_song.find('spotify') > -1):
        return True
    else:
        return False

# write tracks into list file
def feed_tracks(file, tracks):
    with open(file, 'a') as fout:
        for item in tracks['items']:
            track = item['track']
            try:
                fout.write(track['external_urls']['spotify'] + '\n')
            except KeyError:
                title = track['name'] + ' by '+ track['artists'][0]['name']
                print('Skipping track ' + title + ' (local only?)')

# generate filename of the song to be downloaded
def generate_filename(title):
    # IMO python2 sucks dealing with unicode
    title = fix_encoding(title)
    title = fix_decoding(title)
    title = title.replace(' ', '_')
    # slugify removes any special characters
    filename = slugify(title, ok='-_()[]{}', lower=False)
    return fix_encoding(filename)

# please respect these credentials :)
def generate_token():
    creds = oauth2.SpotifyClientCredentials(
        client_id='4fe3fecfe5334023a1472516cc99d805',
        client_secret='0f02b7c483c04257984695007a4a8d5c')
    token = creds.get_access_token()
    return token

def generate_search_URL(song):
    # urllib2.quote() encodes URL with special characters
    URL = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q=" + quote(song)
    return URL

# fix encoding issues in python2
def fix_encoding(query):
    if sys.version_info < (3, 0):
        query = query.encode('utf-8')
    return query

def fix_decoding(query):
    if sys.version_info < (3, 0):
        query = query.decode('utf-8')
    return query

def grace_quit():
    print('')
    print('')
    print('Exitting..')
    sys.exit()
