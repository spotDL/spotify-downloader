# Leaving this be for now, courtesy of Elliot G. (@rocketinventor)

id = 'PU1KSRx70cU&list=RDAMVMPU1KSRx70cU'

import requests
import json
from urllib import request, parse

query = "Ira Ivory Rasmus"

api_key = 'AIzaSyC9XL3ZjWddXya6X74dJoCTL-WEYFDNX30'
url = "https://music.youtube.com/youtubei/v1/search?alt=json&key=" + api_key
headers = {
  "referer": "https://music.youtube.com/search",
#  "origin": "https://music.youtube.com",
#  "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36 Edg/84.0.522.61",
# "content-type": "application/json"
  }

payload1 = {"context":{"client":{"clientName":"WEB_REMIX","clientVersion":"0.1","hl":"en","gl":"IN","experimentIds":[],"experimentsToken":"","browserName":"Edge Chromium","browserVersion":"84.0.522.61","osName":"Windows","osVersion":"10.0","utcOffsetMinutes":330,"locationInfo":{"locationPermissionAuthorizationStatus":"LOCATION_PERMISSION_AUTHORIZATION_STATUS_UNSUPPORTED"},"musicAppInfo":{"musicActivityMasterSwitch":"MUSIC_ACTIVITY_MASTER_SWITCH_INDETERMINATE","musicLocationMasterSwitch":"MUSIC_LOCATION_MASTER_SWITCH_INDETERMINATE","pwaInstallabilityStatus":"PWA_INSTALLABILITY_STATUS_CAN_BE_INSTALLED"}},"capabilities":{},"request":{"internalExperimentFlags":[{"key":"force_music_enable_outertube_tastebuilder_browse","value":"true"},{"key":"force_music_enable_outertube_search_suggestions","value":"true"},{"key":"force_music_enable_outertube_music_queue","value":"true"},{"key":"force_music_enable_outertube_home_browse","value":"true"},{"key":"force_music_enable_outertube_album_detail_browse","value":"true"},{"key":"force_music_enable_outertube_playlist_detail_browse","value":"true"}],"sessionIndex":{}},"activePlayers":{},"user":{"enableSafetyMode":False}},"query":"sarah schachner assassin's creed origins","suggestStats":{"validationStatus":"VALID","parameterValidationStatus":"VALID_PARAMETERS","clientName":"youtube-music","searchMethod":"ENTER_KEY","inputMethod":"KEYBOARD","originalQuery":"sarah schachner assassin's creed origins","availableSuggestions":[{"index":0,"type":0}],"zeroPrefixEnabled":True,"firstEditTimeMsec":4323,"lastEditTimeMsec":6018}}

payload = {
  "context": {
    "client": {
      "clientName": "WEB_REMIX",
      "clientVersion": "0.1",
    },
  },
  "query": query
}

# import urllib3
# 
# encodedBody = json.dumps(payload)
# 
# manager = urllib3.PoolManager()
# 
# res = manager.request('POST', url, headers=headers, body=encodedBody)
# 
# print(res.read())

print('POST\n')

r = requests.post(url,headers=headers, json=payload, stream=True)

print("Status:", r.status_code)
print("Length:", r.headers.get('content-length'))
#print('Recv: ', len(r.text))
#print("Text:", r.text[:300] + "...\n")

qwer = json.dumps(dict(r.headers), indent=4)
print(qwer)

# print('getting chunks')
# try:
#   contents = b''.join(r.iter_content(224))
#   print(contents.decode('UTF-8'))
#   print('NOERROR')
# except:
#   print(contents.decode('UTF-8'))
#   print('ERROR')

video_id = r.json()\
["contents"]\
["sectionListRenderer"]\
["contents"]\
[0]\
["musicShelfRenderer"]\
["contents"]\
[0]\
["musicResponsiveListItemRenderer"]\
["overlay"]\
["musicItemThumbnailOverlayRenderer"]\
["content"]\
["musicPlayButtonRenderer"]\
["playNavigationEndpoint"]\
["watchEndpoint"]\
["videoId"]


print("https://www.youtube.com/watch?v=" + video_id)
print('\n\n\n\n')
print(r.text)

# WOrks but how to find all matches?

# from pytube import YouTube
# yt=YouTube(link)
# t=yt.streams.filter(only_audio=True).all()
# t[0].download(/path)