# setup-storage
termux-setup-storage

# update packages
pkg update -y

# install python and ffmpeg
pkg install -y python ffmpeg

# install spotdl
pip install -U spotdl

if [ ! -d "$HOME/bin" ]; then
    mkdir "$HOME/bin"
fi

if [ ! -f "$HOME/bin/termux-url-opener" ]; then
    touch $HOME/bin/termux-url-opener
fi

curl -L https://raw.githubusercontent.com/spotDL/spotify-downloader/master/termux/termux-url-opener > $HOME/bin/termux-url-opener