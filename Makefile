CODE_FOLDERS = spotdl spotdl/console spotdl/download spotdl/providers spotdl/providers/audio spotdl/providers/lyrics spotdl/types spotdl/utils
PYTHON ?= /usr/bin/env python3
spotdl: spotdl/*.py spotdl/*/*.py
	mkdir -p zip
	for d in $(CODE_FOLDERS) ; do \
	  mkdir -p zip/$$d ;\
	  cp -pPR $$d/*.py zip/$$d/ ;\
	done
	touch -t 200001010101 zip/spotdl/*.py zip/spotdl/**/*.py
	mv zip/spotdl/__main__.py zip/
	cd zip ; zip -q -r ../spotdl spotdl/**.py spotdl/**/* spotdl/**/*.py __main__.py
	rm -rf zip
	echo '#!$(PYTHON)' > spotdl_bin
	cat spotdl.zip >> spotdl_bin
	rm spotdl.zip
	chmod a+x spotdl_bin
