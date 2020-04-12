from spotdl.authorize.services import AuthorizeSpotify
from spotdl import command_line

def match_arguments(arguments):
    if arguments.tracks:
        # TODO: Also support reading from stdin for -t parameter
        # Also supported writing to stdout for all parameters
        if len(arguments.tracks) > 1:
            # log.warning("download multiple tracks with optimized list instead")
            pass
        for track in arguments.tracks:
            command_line.helpers.download_track(track, arguments)
    elif arguments.list:
        if arguments.write_m3u:
            youtube_tools.generate_m3u(
                track_file=arguments.list
            )
        else:
            command_line.helpers.download_tracks_from_file(
                arguments.list,
                arguments,
            )
            # list_dl = downloader.ListDownloader(
            #     tracks_file=arguments.list,
            #     skip_file=arguments.skip,
            #     write_successful_file=arguments.write_successful,
            # )
            # list_dl.download_list()
    elif arguments.playlist:
        spotify_tools.write_playlist(
            playlist_url=arguments.playlist, text_file=arguments.write_to
        )
    elif arguments.album:
        spotify_tools.write_album(
            album_url=arguments.album, text_file=arguments.write_to
        )
    elif arguments.all_albums:
        spotify_tools.write_all_albums_from_artist(
            artist_url=arguments.all_albums, text_file=arguments.write_to
        )
    elif arguments.username:
        spotify_tools.write_user_playlist(
            username=arguments.username, text_file=arguments.write_to
        )


def main():
    arguments = command_line.get_arguments()

    AuthorizeSpotify(
        client_id=arguments.spotify_client_id,
        client_secret=arguments.spotify_client_secret
    )
    # youtube_tools.set_api_key()

    # logzero.setup_default_logger(formatter=const._formatter, level=const.args.log_level)

    try:
        match_arguments(arguments)
    except KeyboardInterrupt as e:
        # log.exception(e)
        sys.exit(2)


if __name__ == "__main__":
    main()

