def format_string(string, metadata, output_extension="", sanitizer=lambda s: s):
    formats = {
        "{track-name}"   : metadata["name"],
        "{artist}"       : metadata["artists"][0]["name"],
        "{album}"        : metadata["album"]["name"],
        "{album-artist}" : metadata["artists"][0]["name"],
        "{genre}"        : metadata["genre"],
        "{disc-number}"  : metadata["disc_number"],
        "{duration}"     : metadata["duration"],
        "{year}"         : metadata["year"],
        "{original-date}": metadata["release_date"],
        "{track-number}" : metadata["track_number"],
        "{total-tracks}" : metadata["total_tracks"],
        "{isrc}"         : metadata["external_ids"]["isrc"],
        # TODO: Call `str.zfill` fill on track-id
        "{track-id}"     : metadata.get("id", ""),
        "{output-ext}"   : output_extension,
    }

    for key, value in formats.items():
        string = string.replace(key, sanitizer(str(value)))

    return string

