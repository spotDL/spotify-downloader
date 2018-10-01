import os

from spotdl import const
from spotdl.main import download_list

import loader

loader.load_defaults()


def test_dry_download_list(tmpdir):
    song = 'http://open.spotify.com/track/0JlS7BXXD07hRmevDnbPDU'
    const.args.folder = str(tmpdir)
    const.args.dry_run = True
    file_path = os.path.join(const.args.folder, 'test_list.txt')
    with open(file_path, 'w') as tin:
        tin.write(song)
    downloaded_song, *_ = download_list(file_path)
    assert downloaded_song == song
