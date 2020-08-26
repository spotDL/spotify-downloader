import requests
import json
from ast import literal_eval as Parse

class YouTubeMusic():
    """
    Make searches on the YT-Music API
    """

    def __init__(self):
        self.api_key = 'AIzaSyC9XL3ZjWddXya6X74dJoCTL-WEYFDNX30'
        self.request_url = 'https://music.youtube.com/youtubei/v1/{}?alt=json&key=' + self.api_key
        self.referer_url = 'https://music.youtube.com/'
        self.headers = {"Referer": self.referer_url}
        self.base_request = {
          "context": {
            "client": {
              "clientName": "WEB_REMIX",
              "clientVersion": "0.1",
            },
          },
          # "query": query
        }

    def generate_request_url(self, method):
        return self.request_url.format(method)

    def request(self, method, body={}):
        if body == {}:
            body = self.base_request
        r = requests.post(self.generate_request_url(method), headers=self.headers, data=json.dumps(body))
        return r.text.replace('\\"', "'")

    def get_inner_text(self, key_text, json_text, key_title='text'):
        return json_text.split(key_text)[1]\
        .split(key_title)[1].split('"')[2]

    def browse(self):
        return

    def getVideoMetadata(self, video_id):
        self.base_request.update({
            "enablePersistentPlaylistPanel": True,
            "videoId": video_id
        })
        json_text = self.request('next')
        # using double quotes b/c it is copied from the JSON
        try:
            album_name = self.get_inner_text("albumName", json_text)
        except IndexError:
            album_name = ''
        artist_name = self.get_inner_text("shortBylineText", json_text)
        length_text = self.get_inner_text("lengthText", json_text)
        song_name = self.get_inner_text("playlistPanelVideoRenderer", json_text)
        thumbnails = json_text.split('"thumbnails": [')[1].split(']')[0]
        thumbnails = Parse('[' + thumbnails + ']')
        thumbnail_url = thumbnails[-2]['url']
        video_url = "https://www.youtube.com/watch?v=" + video_id
        return {
            'title': f'{artist_name} - {song_name}',
            'duration': length_text,
            'url': video_url,
            'album': album_name,
            'artist': artist_name,
            'song': song_name,
            'thumbnail': thumbnail_url
        }

    def search(self, query):
        self.base_request['query'] = query
        json_text = self.request('search')
        video_id = json_text.split('videoId')[1].split('"')[2]
        return self.getVideoMetadata(video_id)