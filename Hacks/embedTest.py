from mutagen.easyid3 import EasyID3, ID3
from mutagen.id3 import APIC, TCOP

from urllib.request import urlopen

# So apparently, the album art applying works but, it doesn't display on 
# windows explorer

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
    cached_albumart = urlopen(metadata["url"]
    ).read()
try:
    audiofile.add(
        APIC(data=cached_albumart,
    ))
except IndexError:
    pass
audiofile.save(v2_version=3)

#print(open(r'D:\Projects\GitHub\spotify-downloader\Hacks\divinity.mp3', 'rb').read())

#From stack

from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error, TRCK, TIT2, TPE1, TALB, TDRC, TCON

audio = MP3(r'D:\Projects\GitHub\spotify-downloader\Hacks\divinity.mp3', ID3=ID3)
audio.tags.delete(r'D:\Projects\GitHub\spotify-downloader\Hacks\divinity.mp3', delete_v1=True, delete_v2=True)
audio.tags.add(
    APIC(
        encoding=3,
        mime='image/jpeg',
        type=3,
        desc=u'Cover',
        data=open(r'D:/Projects/GitHub/spotify-downloader/Hacks/cover.jpg', 'rb').read()
    )
)
audio.save(r'D:\Projects\GitHub\spotify-downloader\Hacks\divinity.mp3', v2_version=3, v1=2)