#!/usr/bin/env python

# -*- coding: UTF-8 -*-

from core import metadata
from core import misc
from bs4 import BeautifulSoup
from titlecase import titlecase
from slugify import slugify
import spotipy
import pafy
import sys
import os
import subprocess

# urllib2 is urllib.request in python3
try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

# decode spotify link to "[artist] - [song]"
def generate_songname(raw_song):
    if misc.is_spotify(raw_song):
        tags = generate_metadata(raw_song)
        raw_song = tags['artists'][0]['name'] + ' - ' + tags['name']
    return misc.fix_encoding(raw_song)

# fetch song's metadata from spotify
def generate_metadata(raw_song):
    if misc.is_spotify(raw_song):
        # fetch track information directly if it is spotify link
        meta_tags = spotify.track(raw_song)
    else:
        # otherwise search on spotify and fetch information from first result
        meta_tags = spotify.search(raw_song, limit=1)['tracks']['items'][0]

    artist = spotify.artist(meta_tags['artists'][0]['id'])
    album = spotify.album(meta_tags['album']['id'])

    try:
        meta_tags[u'genre'] = titlecase(artist['genres'][0])
    except IndexError:
        meta_tags[u'genre'] = None
    try:
        meta_tags[u'copyright'] = album['copyrights'][0]['text']
    except IndexError:
        meta_tags[u'copyright'] = None

    meta_tags[u'release_date'] = album['release_date']
    meta_tags[u'publisher'] = album['label']
    meta_tags[u'total_tracks'] = album['tracks']['total']
    #import pprint
    #pprint.pprint(meta_tags)
    #pprint.pprint(spotify.album(meta_tags['album']['id']))
    return meta_tags

def generate_YouTube_URL(raw_song):
    # decode spotify http link to "[artist] - [song]"
    song = generate_songname(raw_song)
    # generate direct search YouTube URL
    searchURL = misc.generate_search_URL(song)
    item = urllib2.urlopen(searchURL).read()
    #item = unicode(item, 'utf-8')
    items_parse = BeautifulSoup(item, "html.parser")
    check = 1
    if args.manual:
        links = []
        print(song)
        print('')
        print('0. Skip downloading this song')
        # fetch all video links on first page on YouTube
        for x in items_parse.find_all('h3', {'class': 'yt-lockup-title'}):
            # confirm the video result is not an advertisement
            if not x.find('channel') == -1 or not x.find('googleads') == -1:
                print(str(check) + '. ' + x.get_text())
                links.append(x.find('a')['href'])
                check += 1
        print('')
        # let user select the song to download
        result = misc.input_link(links)
        if result is None:
            return None
    else:
        # get video link of the first YouTube result
        result = items_parse.find_all(attrs={'class': 'yt-uix-tile-link'})[0]['href']
        # confirm the video result is not an advertisement
        # otherwise keep iterating until it is not
        while not result.find('channel') == -1 or not result.find('googleads') == -1:
            result = items_parse.find_all(attrs={'class': 'yt-uix-tile-link'})[check]['href']
            check += 1
    full_link = "youtube.com" + result
    return full_link

# parse track from YouTube
def go_pafy(raw_song):
    # video link of the video to extract audio from
    trackURL = generate_YouTube_URL(raw_song)
    if trackURL is None:
        return None
    else:
        # parse the YouTube video
        return pafy.new(trackURL)

# title of the YouTube video
def get_YouTube_title(content, number):
    title = misc.fix_encoding(content.title)
    if number is None:
        return title
    else:
        return str(number) + '. ' + title

# fetch user playlists when using -u option
def feed_playlist(username):
    # fetch all user playlists
    playlists = spotify.user_playlists(username)
    links = []
    check = 1
    # iterate over user playlists
    for playlist in playlists['items']:
        print(str(check) + '. ' + misc.fix_encoding(playlist['name']) + ' (' + str(playlist['tracks']['total']) + ' tracks)')
        links.append(playlist)
        check += 1
    print('')
    # let user select playlist
    playlist = misc.input_link(links)
    # fetch detailed information for playlist
    results = spotify.user_playlist(playlist['owner']['id'], playlist['id'], fields="tracks,next")
    print('')
    # slugify removes any special characters
    file = slugify(playlist['name'], ok='-_()[]{}') + '.txt'
    print('Feeding ' + str(playlist['tracks']['total']) + ' tracks to ' + file)
    tracks = results['tracks']
    # write tracks to file
    misc.feed_tracks(file, tracks)
    # check if there are more pages
    # 1 page = 50 results
    while tracks['next']:
        tracks = spotify.next(tracks)
        misc.feed_tracks(file, tracks)

def download_song(content):
    if args.input_ext == '.webm':
        # best available audio in .webm
        link = content.getbestaudio(preftype='webm')
    elif args.input_ext == '.m4a':
        # best available audio in .webm
        link = content.getbestaudio(preftype='m4a')
    else:
        return False

    if link is None:
        return False
    else:
        music_file = misc.generate_filename(content.title)
        # download link
        link.download(filepath='Music/' + music_file + args.input_ext)
        return True

# convert song from input_ext to output_ext
def convert_song(music_file):
    # skip conversion if input_ext == output_ext
    if not args.input_ext == args.output_ext:
        music_file = music_file.encode('utf-8')
        print('Converting ' + music_file + args.input_ext + ' to ' + args.output_ext[1:])
        if args.avconv:
            convert_with_avconv(music_file)
        else:
            convert_with_FFmpeg(music_file)
        os.remove('Music/' + music_file + args.input_ext)

def convert_with_avconv(music_file):
    # different path for windows
    if os.name == 'nt':
        avconv_path = 'Scripts\\avconv.exe'
    else:
        avconv_path = 'avconv'

    if args.verbose:
        level = 'debug'
    else:
        level = '0'

    command = [avconv_path,
               '-loglevel', level,
               '-i',        'Music/' + music_file + args.input_ext,
               '-ab',       '192k',
               'Music/' + music_file + args.output_ext]

    subprocess.call(command)


def convert_with_FFmpeg(music_file):
    # What are the differences and similarities between ffmpeg, libav, and avconv?
    # https://stackoverflow.com/questions/9477115
    # ffmeg encoders high to lower quality
    # libopus > libvorbis >= libfdk_aac > aac > libmp3lame
    # libfdk_aac due to copyrights needs to be compiled by end user
    # on MacOS brew install ffmpeg --with-fdk-aac will do just that. Other OS?
    # https://trac.ffmpeg.org/wiki/Encode/AAC

    if os.name == "nt":
        ffmpeg_pre = 'Scripts\\ffmpeg.exe '
    else:
        ffmpeg_pre = 'ffmpeg '

    ffmpeg_pre += '-y '
    if not args.verbose:
        ffmpeg_pre += '-hide_banner -nostats -v panic '

    if args.input_ext == '.m4a':
        if args.output_ext == '.mp3':
            ffmpeg_params = '-codec:v copy -codec:a libmp3lame -q:a 2 '
        elif output_ext == '.webm':
            ffmpeg_params = '-c:a libopus -vbr on -b:a 192k -vn '
    elif args.input_ext == '.webm':
        if args.output_ext == '.mp3':
            ffmpeg_params = ' -ab 192k -ar 44100 -vn '
        elif args.output_ext == '.m4a':
	            ffmpeg_params = '-cutoff 20000 -c:a libfdk_aac -b:a 192k -vn '

    command = (ffmpeg_pre +
              '-i Music/' + music_file + args.input_ext + ' ' +
               ffmpeg_params +
              'Music/' + music_file + args.output_ext + '').split(' ')

    subprocess.call(command)

# check if input song already exists in Music folder
def check_exists(music_file, raw_song, islist):
    files = os.listdir("Music")
    for file in files:
        if file.endswith(".temp"):
            os.remove("Music/" + file)
            continue
        # check if any file with similar name is already present in Music/
        dfile = misc.fix_decoding(file)
        umfile = misc.fix_decoding(misc.generate_filename(music_file))
        if dfile.startswith(umfile):
            # check if the already downloaded song has correct metadata
            already_tagged = metadata.compare(file, generate_metadata(raw_song))
            # if not, remove it and download again without prompt
            if misc.is_spotify(raw_song) and not already_tagged:
                os.remove("Music/" + file)
                return False
            # do not prompt and skip the current song if already downloaded when using list
            if islist:
                return True
            # if downloading only single song, prompt to re-download
            else:
                prompt = misc.user_input('Song with same name has already been downloaded. Re-download? (y/n): ').lower()
                if prompt == "y":
                    os.remove("Music/" + file)
                    return False
                else:
                    return True

# download songs from list
def grab_list(file):
    with open(file, 'r') as listed:
        lines = (listed.read()).splitlines()
    # ignore blank lines in file (if any)
    try:
        lines.remove('')
    except ValueError:
        pass
    print('Total songs in list = ' + str(len(lines)) + ' songs')
    print('')
    # nth input song
    number = 1
    for raw_song in lines:
        try:
            grab_single(raw_song, number=number)
        # token expires after 1 hour
        except spotipy.oauth2.SpotifyOauthError:
            # refresh token when it expires
            token = misc.generate_token()
            global spotify
            spotify = spotipy.Spotify(auth=token)
            grab_single(raw_song, number=number)
        # detect network problems
        except (urllib2.URLError, TypeError, IOError):
            lines.append(raw_song)
            # remove the downloaded song from .txt
            misc.trim_song(file)
            # and append it to the last line in .txt
            with open(file, 'a') as myfile:
                myfile.write(raw_song)
            print('Failed to download song. Will retry after other songs.')
            continue
        except KeyboardInterrupt:
            misc.grace_quit()
        finally:
            print('')
        misc.trim_song(file)
        number += 1

# logic behind downloading some song
def grab_single(raw_song, number=None):
    # check if song is being downloaded from list
    if number:
        islist = True
    else:
        islist = False
    content = go_pafy(raw_song)
    if content is None:
        return
    # print "[number]. [artist] - [song]" if downloading from list
    # otherwise print "[artist] - [song]"
    print(get_YouTube_title(content, number))
    # generate file name of the song to download
    music_file = misc.generate_filename(content.title)
    music_file = misc.fix_decoding(music_file)
    if not check_exists(music_file, raw_song, islist=islist):
        if download_song(content):
            print('')
            convert_song(music_file)
            meta_tags = generate_metadata(raw_song)
            if not args.no_metadata:
                metadata.embed(music_file, meta_tags, args.output_ext)
        else:
            print('No audio streams available')

if __name__ == '__main__':

    os.chdir(sys.path[0])
    if not os.path.exists("Music"):
        os.makedirs("Music")

    # token is mandatory when using Spotify's API
    # https://developer.spotify.com/news-stories/2017/01/27/removing-unauthenticated-calls-to-the-web-api/
    token = misc.generate_token()
    spotify = spotipy.Spotify(auth=token)

    # set up arguments
    args = misc.get_arguments()

    if args.song:
        grab_single(raw_song=args.song)
    elif args.list:
        grab_list(file=args.list)
    elif args.username:
        feed_playlist(username=args.username)
