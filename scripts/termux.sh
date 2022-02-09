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

cat > $HOME/bin/termux-url-opener <<EOL
#!/data/data/com.termux/files/usr/bin/bash
SONGS="$HOME/storage/shared/songs"
SPOTDL="/data/data/com.termux/files/usr/bin/spotdl"
if [[ $1 == *"open.spotify.com"* ]]; then
    if [[ ! -d $SONGS ]]; then
        mkdir $SONGS
    fi
    cd $SONGS
    $SPOTDL "$1"
    read -n 1 -s -p "Press Any Key To Exit."
fi
EOL