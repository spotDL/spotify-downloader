from bs4 import BeautifulSoup
import urllib
import pafy
from logzero import logger as log

from spotdl import internals
from spotdl import const

import os
import pprint

# Fix download speed throttle on short duration tracks
# Read more on mps-youtube/pafy#199
pafy.g.opener.addheaders.append(('Range', 'bytes=0-'))


def set_api_key():
    if const.args.youtube_api_key:
        key = const.args.youtube_api_key
    else:
        # Please respect this YouTube token :)
        key = 'AIzaSyC6cEeKlxtOPybk9sEe5ksFN5sB-7wzYp0'
    pafy.set_api_key(key)


def go_pafy(raw_song, meta_tags=None):
    """ Parse track from YouTube. """
    if internals.is_youtube(raw_song):
        track_info = pafy.new(raw_song)
    else:
        track_url = generate_youtube_url(raw_song, meta_tags)

        if track_url:
            track_info = pafy.new(track_url)
        else:
            track_info = None

    return track_info


def get_youtube_title(content, number=None):
    """ Get the YouTube video's title. """
    title = content.title
    if number:
        return '{0}. {1}'.format(number, title)
    else:
        return title


def download_song(file_name, content, quiet=False):
    """ Download the audio file from YouTube. """
    _, extension = os.path.splitext(file_name)
    if extension in ('.webm', '.m4a'):
        link = content.getbestaudio(preftype=extension[1:])
    else:
        log.debug('No audio streams available for {} type'.format(extension))
        return False

    if link:
        log.debug('Downloading from URL: ' + link.url)
        filepath = os.path.join(const.args.folder, file_name)
        log.debug('Saving to: ' + filepath)
        link.download(filepath=filepath, quiet=quiet)
        return True
    else:
        log.debug('No audio streams available')
        return False


def generate_search_url(query):
    """ Generate YouTube search URL for the given song. """
    # urllib.request.quote() encodes string with special characters
    quoted_query = urllib.request.quote(query)
    # Special YouTube URL filter to search only for videos
    url = 'https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q={0}'.format(quoted_query)
    return url


def is_video(result):
    # ensure result is not a channel
    not_video = result.find('channel') is not None or \
                'yt-lockup-channel' in result.parent.attrs['class'] or \
                'yt-lockup-channel' in result.attrs['class']

    # ensure result is not a mix/playlist
    not_video = not_video or \
               'yt-lockup-playlist' in result.parent.attrs['class']

    # ensure video result is not an advertisement
    not_video = not_video or \
                result.find('googleads') is not None

    video = not not_video
    return video


def generate_youtube_url(raw_song, meta_tags):
    url_fetch = GenerateYouTubeURL(raw_song, meta_tags)
    if const.args.youtube_api_key:
        url = url_fetch.api()
    else:
        url = url_fetch.scrape()
    return url


class GenerateYouTubeURL:
    def __init__(self, raw_song, meta_tags):
        self.raw_song = raw_song
        self.meta_tags = meta_tags

        if meta_tags is None:
            self.search_query = raw_song
        else:
            self.search_query = internals.format_string(const.args.search_format,
                                                        meta_tags, force_spaces=True)

    def _best_match(self, videos):
        """ Select the best matching video from a list of videos. """
        if const.args.manual:
            log.info(self.raw_song)
            log.info('0. Skip downloading this song.\n')
            # fetch all video links on first page on YouTube
            for i, v in enumerate(videos):
                log.info(u'{0}. {1} {2} {3}'.format(i+1, v['title'], v['videotime'],
                      "http://youtube.com/watch?v="+v['link']))
            # let user select the song to download
            result = internals.input_link(videos)
            if result is None:
                return None
        else:
            if not self.meta_tags:
                # if the metadata could not be acquired, take the first result
                # from Youtube because the proper song length is unknown
                result = videos[0]
                log.debug('Since no metadata found on Spotify, going with the first result')
            else:
                # filter out videos that do not have a similar length to the Spotify song
                duration_tolerance = 10
                max_duration_tolerance = 20
                possible_videos_by_duration = []

                # start with a reasonable duration_tolerance, and increment duration_tolerance
                # until one of the Youtube results falls within the correct duration or
                # the duration_tolerance has reached the max_duration_tolerance
                while len(possible_videos_by_duration) == 0:
                    possible_videos_by_duration = list(filter(lambda x: abs(x['seconds'] - self.meta_tags['duration']) <= duration_tolerance, videos))
                    duration_tolerance += 1
                    if duration_tolerance > max_duration_tolerance:
                        log.error("{0} by {1} was not found.\n".format(self.meta_tags['name'], self.meta_tags['artists'][0]['name']))
                        return None

                result = possible_videos_by_duration[0]

        if result:
            url = "http://youtube.com/watch?v={0}".format(result['link'])
        else:
            url = None

        return url

    def scrape(self, bestmatch=True, tries_remaining=5):
        """ Search and scrape YouTube to return a list of matching videos. """

        # prevents an infinite loop but allows for a few retries
        if tries_remaining == 0:
            log.debug('No tries left. I quit.')
            return

        search_url = generate_search_url(self.search_query)
        log.debug('Opening URL: {0}'.format(search_url))

        item = urllib.request.urlopen(search_url).read()
        items_parse = BeautifulSoup(item, "html.parser")

        videos = []
        for x in items_parse.find_all('div', {'class': 'yt-lockup-dismissable yt-uix-tile'}):

            if not is_video(x):
                continue

            y = x.find('div', class_='yt-lockup-content')
            link = y.find('a')['href'][-11:]
            title = y.find('a')['title']

            try:
                videotime = x.find('span', class_="video-time").get_text()
            except AttributeError:
                log.debug('Could not find video duration on YouTube, retrying..')
                return self.scrape(bestmatch=bestmatch, tries_remaining=tries_remaining-1)

            youtubedetails = {'link': link, 'title': title, 'videotime': videotime,
                              'seconds': internals.get_sec(videotime)}
            videos.append(youtubedetails)

        if bestmatch:
            return self._best_match(videos)

        return videos


    def api(self, bestmatch=True):
        """ Use YouTube API to search and return a list of matching videos. """

        query = { 'part'       : 'snippet',
                  'maxResults' :  50,
                  'type'       : 'video' }

        if const.args.music_videos_only:
            query['videoCategoryId'] = '10'

        if not self.meta_tags:
            song = self.raw_song
            query['q'] = song
        else:
            query['q'] = self.search_query
        log.debug('query: {0}'.format(query))

        data = pafy.call_gdata('search', query)
        data['items'] = list(filter(lambda x: x['id'].get('videoId') is not None,
                                    data['items']))
        query_results = {'part': 'contentDetails,snippet,statistics',
                  'maxResults': 50,
                  'id': ','.join(i['id']['videoId'] for i in data['items'])}
        log.debug('query_results: {0}'.format(query_results))

        vdata = pafy.call_gdata('videos', query_results)

        videos = []
        for x in vdata['items']:
            duration_s = pafy.playlist.parseISO8591(x['contentDetails']['duration'])
            youtubedetails = {'link': x['id'], 'title': x['snippet']['title'],
                              'videotime':internals.videotime_from_seconds(duration_s),
                              'seconds': duration_s}
            videos.append(youtubedetails)

        if bestmatch:
            return self._best_match(videos)

        return videos
