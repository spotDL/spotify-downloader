from mutagen.easyid3 import EasyID3, ID3
from mutagen.id3 import APIC, TCOP

from urllib.request import urlopen

# handler = ID3(r'D:\Projects\GitHub\spotify-downloader\Hacks\divinity.mp3')
# 
binaryIMG = open(r'D:\Projects\GitHub\spotify-downloader\Hacks\cover.jpg', 'rb').read()
# 
# handler['APIC'] = APIC(
#     encoding=3,
#     mime="image/jpeg",
#     type=3,
#     desc=u"Cover",
#     data=binaryIMG
#     )

handler = ID3(r'D:\Projects\GitHub\spotify-downloader\Hacks\divinity.mp3')
audiofile = handler
handler.add(
    TCOP(encoding=3,
    text= '(c) Microsoft by Mikhail Zex')
)

metadata = {
    'url': 'file:///D:/Projects/GitHub/spotify-downloader/Hacks/cover.jpg'
}

cached_albumart = None

if cached_albumart is None:
    cached_albumart = urlopen(
        metadata["url"]
    ).read()
try:
    audiofile.add(
        APIC(           # Other stuff is working just fine, why not album art
        encoding=3,     # stackOverflow Tmrw then
        mime="image/jpeg",
        type=3,
        desc=u"Cover",
        data=cached_albumart,
    ))
except IndexError:
    pass
audiofile.save(v2_version=3)

#print(open(r'D:\Projects\GitHub\spotify-downloader\Hacks\divinity.mp3', 'rb').read())