#!/bin/bash

CODE_FOLDERS="spotdl spotdl/console spotdl/download spotdl/providers spotdl/providers/audio spotdl/providers/lyrics spotdl/types spotdl/utils"
PYTHON="/usr/bin/env python3"

mkdir -p zip

for d in $CODE_FOLDERS; do
    mkdir -p "zip/$d"
    cp -pPR "$d"/*.py "zip/$d/"
done

touch -t 200001010101 zip/spotdl/*.py zip/spotdl/**/*.py
mv zip/spotdl/__main__.py zip/
cd zip
zip -q -r spotdl spotdl/**.py spotdl/**/* spotdl/**/*.py __main__.py
mv spotdl.zip ../spotdl.zip
cd ..
rm -rf zip

echo '#!'"$PYTHON" > spotDL
cat spotdl.zip >> spotDL
rm spotdl.zip
chmod a+x spotDL
