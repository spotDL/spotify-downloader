#!/bin/bash

playlists=(
            'https://open.spotify.com/playlist/3SnBkikg75VeyH7QRZLN5H?si=9_x3YEppTVKhGkVVaQLUHQ'
            'https://open.spotify.com/playlist/2o0JEpwxPOMRlPClN9W8Pt?si=EydQB1PLQt-4OrMVpkX_oA'
            'https://open.spotify.com/playlist/6Ua80N8kOGcnAZNCYVUwP8?si=REeS0jtsS86bAFWPkUp_FA'
            'https://open.spotify.com/playlist/37i9dQZF1EpmzUbuNBG7yP?si=Go7-Y_VzQ5yOje5JZv61lw'
            'https://open.spotify.com/playlist/37i9dQZF1E9NTscgVJZuAm?si=WC78B_AERSqnghenSfWonQ'
            'https://open.spotify.com/playlist/7BgO0Cr0kKECbKQukMmtRd?si=EPv8E43kQFiYPwiVjlNqsw'
            'https://open.spotify.com/playlist/53RNAtZSEdsfMwrm6hrFZs?si=gEhRZYg-S6GxaIvAQugOUg'
            )

rm *.txt;
for i in "${playlists[@]}"
do 
    echo "$i";
    LIST_FILENAME=$(spotdl --playlist $i 2>&1 | grep "INFO" | grep "Writing" | awk '{print $6}')
    echo "playlist listname $LIST_FILENAME"
    PL_NAME=(${LIST_FILENAME//./ })
    echo "playlist name: $PL_NAME"
    mkdir $PL_NAME;
    spotdl -ll DEBUG --list $LIST_FILENAME --overwrite skip --trim-silence -f "./$PL_NAME" --prefix -ff "{artist} - {track_name}";
done;