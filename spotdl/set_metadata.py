import os
import subprocess

from logzero import logger as log

from spotdl import metadata, const, spotify_tools


def create_file(input_file, link):
    log.info("Get metadata for {}".format(input_file))
    try:
        file_ext = '.{}'.format(input_file.split('.')[-1])
    except Exception as e:
        file_ext = ''

    meta_tags = spotify_tools.generate_metadata(link)
    if not meta_tags:
        log.error("No metadata found.")
    else:
        file_name = "{} - {}{}".format(meta_tags["artists"][0]["name"], meta_tags["name"], file_ext)
        log.info("Create {}".format(file_name))
        output_file = os.path.join(const.args.folder, file_name)
        command = (
                "ffmpeg -y -nostdin -hide_banner -nostats -v panic -i".split()
                + [input_file]
                + "-c copy -map_metadata -1 -map 0".split()
                + [output_file]
        )

        try:
            subprocess.call(command)
            metadata.embed(output_file, meta_tags)
        except Exception as e:
            log.error(str(e))
