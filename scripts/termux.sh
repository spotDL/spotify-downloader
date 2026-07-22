# setup-storage
termux-setup-storage

# update packages and add python3.13 to available packages
pkg update -y
pkg install -y tur-repo
pkg update -y

# install python3.13 and ffmpeg
pkg install -y python3.13 ffmpeg rust binutils

# install spotdl
python3.13 -m ensurepip --upgrade
python3.13 -m pip install -U spotdl

if [ ! -d "$HOME/bin" ]; then
    mkdir "$HOME/bin"
fi

if [ ! -f "$HOME/bin/termux-url-opener" ]; then
    touch $HOME/bin/termux-url-opener
fi

cat > $HOME/bin/termux-url-opener <<'EOL'
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
