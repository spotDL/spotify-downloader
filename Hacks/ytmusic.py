# Leaving this be for now, courtesy of Elliot G. (@rocketinventor)

import requests
import json

query = "Ira Ivory Rasmus"

api_key = 'AIzaSyC9XL3ZjWddXya6X74dJoCTL-WEYFDNX30'
url = "https://music.youtube.com/youtubei/v1/search?alt=json&key=" + api_key
headers = {
  "referer": "https://music.youtube.com/search",
  }

payload = {
  "context": {
    "client": {
      "clientName": "WEB_REMIX",
      "clientVersion": "0.1",
    },
  },
  "query": query
}

r = requests.post(url,headers=headers, json=payload, stream=True)

print('Status:', r.status_code)
print('\nMatches:')

# qwer = json.dumps(dict(r.headers), indent=4)
# print(qwer)

video_ids = []
for chunk in r.text.split('videoId')[1:]:
    id = chunk.split('"')[2]
    if id not in video_ids:
        # print(id)
        video_ids.append(id)

# print(video_ids)

for video_id in video_ids:
    print("https://www.youtube.com/watch?v=" + video_id)