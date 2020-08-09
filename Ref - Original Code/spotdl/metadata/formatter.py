def format_string(string, metadata, output_extension="", sanitizer=lambda s: s):
    """
    Replaces any special tags contained in the string with their
    metadata values.

    Parameters
    ----------
    string: `str`
        A string containing any special tags.

    metadata: `dict`
        Metadata in standardized form.

    output_extension: `str`
        This is used to replace the special tag *"{output-ext}"* (if any)
        in the ``string`` passed.

    sanitizer: `function`
        This sanitizer function is called on every metadata value
        before replacing it with its special tag.

    Returns
    -------
    string: `str`
        A string with all special tags replaced with their
        corresponding metadata values.

    Examples
    --------
    + Formatting the string *"{artist} - {track-name}"* with metadata
      from YouTube:

        >>> from spotdl.metadata_search import MetadataSearch
        >>> searcher = MetadataSearch("ncs spectre")
        >>> metadata = searcher.on_youtube()
        >>> from spotdl.metadata import format_string
        >>> string = format_string("{artist} - {track-name}", metadata)
        >>> string
        'NoCopyrightSounds - Alan Walker - Spectre [NCS Release]'
    """

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
        "{track-number}" : str(metadata["track_number"]).zfill(len(str(metadata["total_tracks"]))),
        "{total-tracks}" : metadata["total_tracks"],
        "{isrc}"         : metadata["external_ids"]["isrc"],
        "{track-id}"     : metadata.get("id", ""),
        "{output-ext}"   : output_extension,
    }

    for key, value in formats.items():
        string = string.replace(key, sanitizer(str(value)))

    return string

