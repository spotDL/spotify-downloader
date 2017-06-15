#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from core.misc import input_link
from core.misc import trim_song
from core.misc import get_arguments
from core.misc import is_spotify
from core.misc import generate_token
from core.misc import generate_search_URL
from core.misc import fix_encoding
from core.misc import grace_quit
from bs4 import BeautifulSoup
from titlecase import titlecase
from slugify import slugify
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4, MP4Cover
import spotipy
import spotipy.oauth2 as oauth2
import urllib2
import pafy
import sys
import os
import subprocess

def generate_song_name(raw_song):
    if is_spotify(raw_song):
        tags = generate_metadata(raw_song)
        raw_song = tags['artists'][0]['name'] + ' - ' + tags['name']
    return raw_song

def generate_metadata(raw_song):
    try:
        if is_spotify(raw_song):
            meta_tags = spotify.track(raw_song)
        else:
            meta_tags = spotify.search(raw_song, limit=1)['tracks']['items'][0]
        artist_id = spotify.artist(meta_tags['artists'][0]['id'])

        try:
            meta_tags[u'genre'] = titlecase(artist_id['genres'][0])
        except IndexError:
            meta_tags[u'genre'] = None

        meta_tags[u'release_date'] = spotify.album(meta_tags['album']['id'])['release_date']
        meta_tags[u'copyright'] = spotify.album(meta_tags['album']['id'])['copyrights'][0]['text']
        meta_tags[u'publisher'] = spotify.album(meta_tags['album']['id'])['label']
        meta_tags[u'total_tracks'] = spotify.album(meta_tags['album']['id'])['tracks']['total']
        import pprint
        pprint.pprint(meta_tags)
        #pprint.pprint(spotify.album(meta_tags['album']['id']))
        return meta_tags

    except BaseException:
        return None

def generate_YouTube_URL(raw_song):
    song = generate_song_name(raw_song)
    searchURL = generate_search_URL(song)
    item = urllib2.urlopen(searchURL).read()
    items_parse = BeautifulSoup(item, "html.parser")
    check = 1
    if args.manual:
        links = []
        print(song)
        print('')
        print('0. Skip downloading this song')
        for x in items_parse.find_all('h3', {'class': 'yt-lockup-title'}):
            if not x.find('channel') == -1 or not x.find('googleads') == -1:
                print(str(check) + '. ' + x.get_text())
                links.append(x.find('a')['href'])
                check += 1
        print('')
        result = input_link(links)
        if result is None:
            return None
    else:
        result = items_parse.find_all(
            attrs={'class': 'yt-uix-tile-link'})[0]['href']
        while not result.find('channel') == - \
                1 or not result.find('googleads') == -1:
            result = items_parse.find_all(
                attrs={'class': 'yt-uix-tile-link'})[check]['href']
            check += 1
    full_link = "youtube.com" + result
    return full_link

def go_pafy(raw_song):
    trackURL = generate_YouTube_URL(raw_song)
    if trackURL is None:
        return None
    else:
        return pafy.new(trackURL)

def get_YouTube_title(content, number):
    title = content.title
    if number is None:
        return title
    else:
        return str(number) + '. ' + title

def feed_tracks(file, tracks):
    with open(file, 'a') as fout:
        for item in tracks['items']:
            track = item['track']
            try:
                fout.write(track['external_urls']['spotify'] + '\n')
            except KeyError:
                pass

def feed_playlist(username):
    playlists = spotify.user_playlists(username)
    links = []
    check = 1
    for playlist in playlists['items']:
        print(str(check) + '. ' + fix_encoding(playlist['name']) + ' (' + str(playlist['tracks']['total']) + ' tracks)')
        links.append(playlist)
        check += 1
    print('')
    playlist = input_link(links)
    results = spotify.user_playlist(playlist['owner']['id'], playlist['id'], fields="tracks,next")
    print('')
    file = slugify(playlist['name'], ok='-_()[]{}') + '.txt'
    print('Feeding ' + str(playlist['tracks']['total']) + ' tracks to ' + file)
    tracks = results['tracks']
    feed_tracks(file, tracks)
    while tracks['next']:
        tracks = spotify.next(tracks)
        feed_tracks(file, tracks)

# Generate name for the song to be downloaded
def generate_filename(content):
    title = (content.title).replace(' ', '_')
    title = slugify(title, ok='-_()[]{}', lower=False)
    return fix_encoding(title)

def download_song(content):
    music_file = generate_filename(content)
    if args.input_ext == '.webm':
        link = content.getbestaudio(preftype='webm')
        if link is not None:
            link.download(filepath='Music/' + music_file + args.input_ext)
    else:
        link = content.getbestaudio(preftype='m4a')
        if link is not None:
            link.download(filepath='Music/' + music_file + args.input_ext)

def convert_song(music_file):
    if not args.input_ext == args.output_ext:
        print('Converting ' + music_file + args.input_ext + ' to ' + args.output_ext[1:])
        if args.ffmpeg:
            convert_with_FFmpeg(music_file)
        else:
            convert_with_libav(music_file)

def convert_with_libav(music_file):
    if os.name == 'nt':
        avconv_path = 'Scripts\\avconv.exe'
    else:
        avconv_path = 'avconv'

    if args.verbose:
        level = 'debug'
    else:
        level = '0'

    #print([avconv_path,
    #      '-loglevel', level,
    #      '-i',        'Music/' + music_file + args.input_ext,
    #      '-ab',       '192k',
    #      'Music/' + music_file + args.output_ext])

    subprocess.call([avconv_path,
                    '-loglevel', level,
                    '-i',        'Music/' + music_file + args.input_ext,
                    '-ab',       '192k',
                    'Music/' + music_file + args.output_ext])

    os.remove('Music/' + music_file + args.input_ext)

def convert_with_FFmpeg(music_file):
    # What are the differences and similarities between ffmpeg, libav, and avconv?
    # https://stackoverflow.com/questions/9477115
    # ffmeg encoders high to lower quality
    # libopus > libvorbis >= libfdk_aac > aac > libmp3lame
    # libfdk_aac due to copyrights needs to be compiled by end user
    # on MacOS brew install ffmpeg --with-fdk-aac will do just that. Other OS?
    # https://trac.ffmpeg.org/wiki/Encode/AAC
    #
    if os.name == "nt":
        ffmpeg_pre = 'Scripts//ffmpeg.exe '
    else:
        ffmpeg_pre = 'ffmpeg '

    ffmpeg_pre += '-y '
    if not args.verbose:
        ffmpeg_pre += '-hide_banner -nostats -v panic '

    if args.input_ext == '.m4a':
        if args.output_ext == '.mp3':
            ffmpeg_params = ' -codec:v copy -codec:a libmp3lame -q:a 2 '
        elif output_ext == '.webm':
            ffmpeg_params = ' -c:a libopus -vbr on -b:a 192k -vn '
        else:
            return
    elif args.input_ext == '.webm':
        if args.output_ext == '.mp3':
            ffmpeg_params = ' -ab 192k -ar 44100 -vn '
        elif args.output_ext == '.m4a':
	            ffmpeg_params = ' -cutoff 20000 -c:a libfdk_aac -b:a 256k -vn '
        else:
            return
    else:
        print('Unknown formats. Unable to convert.', args.input_ext, args.output_ext)
        return

    #command = (ffmpeg_pre +
    #          '-i "Music/' + music_file + args.input_ext + '"' +
    #           ffmpeg_params +
    #          '"Music/' + music_file + args.output_ext + '"').split(' ')

    commandos = (ffmpeg_pre +
              '-i "Music/' + music_file + args.input_ext + '" ' +
              ffmpeg_params +
              '"Music/' + music_file + args.output_ext + '" ')
    #print(command)
    #print(commandos)
    os.system(commandos)
    #subprocess.call(command)

    os.remove('Music/' + music_file + args.input_ext)

def check_exists(music_file, raw_song, islist):
    files = os.listdir("Music")
    for file in files:
        if file.endswith(".temp"):
            os.remove("Music/" + file)
            continue

        if file.startswith(music_file):
            # FIXME
            #audiofile = mutagen.load("Music/" + music_file + output_ext)
            #if is_spotify(raw_song) and not audiofile.tag.title == (
            #        generate_metadata(raw_song))['name']:
            #    os.remove("Music/" + music_file + output_ext)
            #    return False
            os.remove("Music/" + file)
            return False
        if islist:
            return True
        else:
            prompt = raw_input('Song with same name has already been downloaded. Re-download? (y/n): ').lower()
            if prompt == "y":
                os.remove("Music/" + file)
                return False
            else:
                return True

# Remove song from file once downloaded
def fix_metadata(music_file, meta_tags):
    if meta_tags is None:
        print('Could not find meta-tags')
    elif args.output_ext == '.m4a':
        print('Fixing meta-tags')
        fix_metadata_m4a(music_file, meta_tags)
    elif args.output_ext == '.mp3':
        print('Fixing meta-tags')
        fix_metadata_mp3(music_file, meta_tags)
    else:
         print('Cannot embed meta-tags into given output extension')

def fix_metadata_mp3(music_file, meta_tags):
    audiofile = EasyID3('Music/' + music_file + args.output_ext)
    audiofile['artist'] = meta_tags['artists'][0]['name']
    audiofile['albumartist'] = meta_tags['artists'][0]['name']
    audiofile['album'] = meta_tags['album']['name']
    audiofile['title'] = meta_tags['name']
    audiofile['tracknumber'] = [meta_tags['track_number'], meta_tags['total_tracks']]
    audiofile['discnumber'] = [meta_tags['disc_number'], 0]
    audiofile['date'] = meta_tags['release_date']
    audiofile['originaldate'] = meta_tags['release_date']
    audiofile['copyright'] = meta_tags['copyright']
    audiofile['author'] = meta_tags['artists'][0]['name']
    audiofile['lyricist'] = meta_tags['artists'][0]['name']
    audiofile['arranger'] = meta_tags['artists'][0]['name']
    audiofile['performer'] = meta_tags['artists'][0]['name']
    audiofile['encodedby'] = meta_tags['publisher']
    audiofile['isrc'] = meta_tags['external_ids']['isrc']
    audiofile['website'] = meta_tags['external_urls']['spotify']
    audiofile['length'] = meta_tags['duration_ms'] / 100
    if meta_tags['genre']:
        audiofile['genre'] = meta_tags['genre']
    audiofile.save(v2_version=3)
    audiofile = ID3('Music/' + music_file + args.output_ext)
    albumart = urllib2.urlopen(meta_tags['album']['images'][0]['url'])
    audiofile["APIC"] = APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=albumart.read())
    albumart.close()
    audiofile.save(v2_version=3)

def fix_metadata_m4a(music_file, meta_tags):
    # eyed serves only mp3 not aac so using mutagen
    # Apple has specific tags - see mutagen docs -
    # http://mutagen.readthedocs.io/en/latest/api/mp4.html
    tags = {'album': '\xa9alb',
            'artist': '\xa9ART',
            'date': '\xa9day',
            'title': '\xa9nam',
            'originaldate': 'purd',
            'comment': '\xa9cmt',
            'group': '\xa9grp',
            'writer': '\xa9wrt',
            'genre': '\xa9gen',
            'tracknumber': 'trkn',
            'albumartist': 'aART',
            'disknumber': 'disk',
            'cpil': 'cpil',
            'albumart': 'covr',
            'copyright': 'cprt',
            'tempo': 'tmpo'}

    audiofile = MP4('Music/' + music_file + args.output_ext)
    audiofile[tags['artist']] = meta_tags['artists'][0]['name']
    audiofile[tags['albumartist']] = meta_tags['artists'][0]['name']
    audiofile[tags['album']] = meta_tags['album']['name']
    audiofile[tags['title']] = meta_tags['name']
    audiofile[tags['tracknumber']] = [(meta_tags['track_number'], meta_tags['total_tracks'])]
    audiofile[tags['disknumber']] = [(meta_tags['disc_number'], 0)]
    audiofile[tags['date']] = meta_tags['release_date']
    audiofile[tags['originaldate']] = meta_tags['release_date']
    audiofile[tags['copyright']] = meta_tags['copyright']
    if meta_tags['genre']:
        audiofile[tags['genre']] = meta_tags['genre']
    albumart = urllib2.urlopen(meta_tags['album']['images'][0]['url'])
    audiofile[tags['albumart']] = [ MP4Cover(albumart.read(), imageformat=MP4Cover.FORMAT_JPEG) ]
    albumart.close()
    audiofile.save()


def grab_list(file):
    lines = open(file, 'r').read()
    lines = lines.splitlines()
    # Ignore blank lines in file (if any)
    try:
        lines.remove('')
    except ValueError:
        pass
    print('Total songs in list = ' + str(len(lines)) + ' songs')
    print('')
    # Count the number of song being downloaded
    number = 1
    for raw_song in lines:
        try:
            grab_single(raw_song, number=number)
            trim_song(file)
            number += 1
            print('')
        except KeyboardInterrupt:
            grace_quit()
        except ConnectionError:
            lines.append(raw_song)
            trim_song(file)
            with open(file, 'a') as myfile:
                myfile.write(raw_song)
            print('Failed to download song. Will retry after other songs.')

# Logic behind preparing the song to download to finishing meta-tags
def grab_single(raw_song, number=None):
    if number:
        islist = True
    else:
        islist = False
    content = go_pafy(raw_song)
    if content is None:
        return
    print(get_YouTube_title(content, number))
    music_file = generate_filename(content)
    if not check_exists(music_file, raw_song, islist=islist):
        download_song(content)
        print('')
        convert_song(music_file)
        meta_tags = generate_metadata(raw_song)
        if not args.no_metadata:
            fix_metadata(music_file, meta_tags)

if __name__ == '__main__':

    # Python 3 compatibility
    if sys.version_info > (3, 0):
        raw_input = input

    os.chdir(sys.path[0])
    if not os.path.exists("Music"):
        os.makedirs("Music")

    token = generate_token()
    spotify = spotipy.Spotify(auth=token)

    # Set up arguments
    args = get_arguments()

    if args.song:
        grab_single(raw_song=args.song)
    elif args.list:
        grab_list(file=args.list)
    elif args.username:
        feed_playlist(username=args.username)
