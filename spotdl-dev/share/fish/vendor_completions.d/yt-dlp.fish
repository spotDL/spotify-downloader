
complete --command yt-dlp --long-option help --short-option h --description 'Print this help text and exit'
complete --command yt-dlp --long-option version --description 'Print program version and exit'
complete --command yt-dlp --long-option update --short-option U --description 'Check if updates are available. You installed yt-dlp from a manual build or with a package manager; Use that to update'
complete --command yt-dlp --long-option no-update --description 'Do not check for updates (default)'
complete --command yt-dlp --long-option update-to --description 'Upgrade/downgrade to a specific version. CHANNEL can be a repository as well. CHANNEL and TAG default to "stable" and "latest" respectively if omitted; See "UPDATE" for details. Supported channels: stable, nightly, master'
complete --command yt-dlp --long-option ignore-errors --short-option i --description 'Ignore download and postprocessing errors. The download will be considered successful even if the postprocessing fails'
complete --command yt-dlp --long-option no-abort-on-error --description 'Continue with next video on download errors; e.g. to skip unavailable videos in a playlist (default)'
complete --command yt-dlp --long-option abort-on-error --description 'Abort downloading of further videos if an error occurs (Alias: --no-ignore-errors)'
complete --command yt-dlp --long-option dump-user-agent --description 'Display the current user-agent and exit'
complete --command yt-dlp --long-option list-extractors --description 'List all supported extractors and exit'
complete --command yt-dlp --long-option extractor-descriptions --description 'Output descriptions of all supported extractors and exit'
complete --command yt-dlp --long-option use-extractors --description 'Extractor names to use separated by commas. You can also use regexes, "all", "default" and "end" (end URL matching); e.g. --ies "holodex.*,end,youtube". Prefix the name with a "-" to exclude it, e.g. --ies default,-generic. Use --list-extractors for a list of extractor names. (Alias: --ies)'
complete --command yt-dlp --long-option force-generic-extractor
complete --command yt-dlp --long-option default-search --description 'Use this prefix for unqualified URLs. E.g. "gvsearch2:python" downloads two videos from google videos for the search term "python". Use the value "auto" to let yt-dlp guess ("auto_warning" to emit a warning when guessing). "error" just throws an error. The default value "fixup_error" repairs broken URLs, but emits an error if this is not possible instead of searching'
complete --command yt-dlp --long-option ignore-config --description 'Don'"'"'t load any more configuration files except those given to --config-locations. For backward compatibility, if this option is found inside the system configuration file, the user configuration is not loaded. (Alias: --no-config)'
complete --command yt-dlp --long-option no-config-locations --description 'Do not load any custom configuration files (default). When given inside a configuration file, ignore all previous --config-locations defined in the current file'
complete --command yt-dlp --long-option config-locations --description 'Location of the main configuration file; either the path to the config or its containing directory ("-" for stdin). Can be used multiple times and inside other configuration files'
complete --command yt-dlp --long-option plugin-dirs --description 'Path to an additional directory to search for plugins. This option can be used multiple times to add multiple directories. Use "default" to search the default plugin directories (default)'
complete --command yt-dlp --long-option no-plugin-dirs --description 'Clear plugin directories to search, including defaults and those provided by previous --plugin-dirs'
complete --command yt-dlp --long-option flat-playlist --description 'Do not extract a playlist'"'"'s URL result entries; some entry metadata may be missing and downloading may be bypassed'
complete --command yt-dlp --long-option no-flat-playlist --description 'Fully extract the videos of a playlist (default)'
complete --command yt-dlp --long-option live-from-start --description 'Download livestreams from the start. Currently experimental and only supported for YouTube and Twitch'
complete --command yt-dlp --long-option no-live-from-start --description 'Download livestreams from the current time (default)'
complete --command yt-dlp --long-option wait-for-video --description 'Wait for scheduled streams to become available. Pass the minimum number of seconds (or range) to wait between retries'
complete --command yt-dlp --long-option no-wait-for-video --description 'Do not wait for scheduled streams (default)'
complete --command yt-dlp --long-option mark-watched --description 'Mark videos watched (even with --simulate)'
complete --command yt-dlp --long-option no-mark-watched --description 'Do not mark videos watched (default)'
complete --command yt-dlp --long-option no-colors
complete --command yt-dlp --long-option color --description 'Whether to emit color codes in output, optionally prefixed by the STREAM (stdout or stderr) to apply the setting to. Can be one of "always", "auto" (default), "never", or "no_color" (use non color terminal sequences). Use "auto-tty" or "no_color-tty" to decide based on terminal support only. Can be used multiple times'
complete --command yt-dlp --long-option compat-options --description 'Options that can help keep compatibility with youtube-dl or youtube-dlc configurations by reverting some of the changes made in yt-dlp. See "Differences in default behavior" for details'
complete --command yt-dlp --long-option alias --description 'Create aliases for an option string. Unless an alias starts with a dash "-", it is prefixed with "--". Arguments are parsed according to the Python string formatting mini-language. E.g. --alias get-audio,-X "-S aext:{0},abr -x --audio-format {0}" creates options "--get-audio" and "-X" that takes an argument (ARG0) and expands to "-S aext:ARG0,abr -x --audio-format ARG0". All defined aliases are listed in the --help output. Alias options can trigger more aliases; so be careful to avoid defining recursive options. As a safety measure, each alias may be triggered a maximum of 100 times. This option can be used multiple times'
complete --command yt-dlp --long-option preset-alias --short-option t --description 'Applies a predefined set of options. e.g. --preset-alias mp3. The following presets are available: mp3, aac, mp4, mkv, sleep. See the "Preset Aliases" section at the end for more info. This option can be used multiple times'
complete --command yt-dlp --long-option proxy --description 'Use the specified HTTP/HTTPS/SOCKS proxy. To enable SOCKS proxy, specify a proper scheme, e.g. socks5://user:pass@127.0.0.1:1080/. Pass in an empty string (--proxy "") for direct connection'
complete --command yt-dlp --long-option socket-timeout --description 'Time to wait before giving up, in seconds'
complete --command yt-dlp --long-option source-address --description 'Client-side IP address to bind to'
complete --command yt-dlp --long-option impersonate --description 'Client to impersonate for requests. E.g. chrome, chrome-110, chrome:windows-10. Pass --impersonate="" to impersonate any client. Note that forcing impersonation for all requests may have a detrimental impact on download speed and stability'
complete --command yt-dlp --long-option list-impersonate-targets --description 'List available clients to impersonate.'
complete --command yt-dlp --long-option force-ipv4 --short-option 4 --description 'Make all connections via IPv4'
complete --command yt-dlp --long-option force-ipv6 --short-option 6 --description 'Make all connections via IPv6'
complete --command yt-dlp --long-option enable-file-urls --description 'Enable file:// URLs. This is disabled by default for security reasons.'
complete --command yt-dlp --long-option geo-verification-proxy --description 'Use this proxy to verify the IP address for some geo-restricted sites. The default proxy specified by --proxy (or none, if the option is not present) is used for the actual downloading'
complete --command yt-dlp --long-option cn-verification-proxy
complete --command yt-dlp --long-option xff --description 'How to fake X-Forwarded-For HTTP header to try bypassing geographic restriction. One of "default" (only when known to be useful), "never", an IP block in CIDR notation, or a two-letter ISO 3166-2 country code'
complete --command yt-dlp --long-option geo-bypass
complete --command yt-dlp --long-option no-geo-bypass
complete --command yt-dlp --long-option geo-bypass-country
complete --command yt-dlp --long-option geo-bypass-ip-block
complete --command yt-dlp --long-option playlist-start
complete --command yt-dlp --long-option playlist-end
complete --command yt-dlp --long-option playlist-items --short-option I --description 'Comma separated playlist_index of the items to download. You can specify a range using "[START]:[STOP][:STEP]". For backward compatibility, START-STOP is also supported. Use negative indices to count from the right and negative STEP to download in reverse order. E.g. "-I 1:3,7,-5::2" used on a playlist of size 15 will download the items at index 1,2,3,7,11,13,15'
complete --command yt-dlp --long-option match-title
complete --command yt-dlp --long-option reject-title
complete --command yt-dlp --long-option min-filesize --description 'Abort download if filesize is smaller than SIZE, e.g. 50k or 44.6M'
complete --command yt-dlp --long-option max-filesize --description 'Abort download if filesize is larger than SIZE, e.g. 50k or 44.6M'
complete --command yt-dlp --long-option date --description 'Download only videos uploaded on this date. The date can be "YYYYMMDD" or in the format [now|today|yesterday][-N[day|week|month|year]]. E.g. "--date today-2weeks" downloads only videos uploaded on the same day two weeks ago'
complete --command yt-dlp --long-option datebefore --description 'Download only videos uploaded on or before this date. The date formats accepted are the same as --date'
complete --command yt-dlp --long-option dateafter --description 'Download only videos uploaded on or after this date. The date formats accepted are the same as --date'
complete --command yt-dlp --long-option min-views
complete --command yt-dlp --long-option max-views
complete --command yt-dlp --long-option match-filters --description 'Generic video filter. Any "OUTPUT TEMPLATE" field can be compared with a number or a string using the operators defined in "Filtering Formats". You can also simply specify a field to match if the field is present, use "!field" to check if the field is not present, and "&" to check multiple conditions. Use a "\" to escape "&" or quotes if needed. If used multiple times, the filter matches if at least one of the conditions is met. E.g. --match-filters !is_live --match-filters "like_count>?100 & description~='"'"'(?i)\bcats \& dogs\b'"'"'" matches only videos that are not live OR those that have a like count more than 100 (or the like field is not available) and also has a description that contains the phrase "cats & dogs" (caseless). Use "--match-filters -" to interactively ask whether to download each video'
complete --command yt-dlp --long-option no-match-filters --description 'Do not use any --match-filters (default)'
complete --command yt-dlp --long-option break-match-filters --description 'Same as "--match-filters" but stops the download process when a video is rejected'
complete --command yt-dlp --long-option no-break-match-filters --description 'Do not use any --break-match-filters (default)'
complete --command yt-dlp --long-option no-playlist --description 'Download only the video, if the URL refers to a video and a playlist'
complete --command yt-dlp --long-option yes-playlist --description 'Download the playlist, if the URL refers to a video and a playlist'
complete --command yt-dlp --long-option age-limit --description 'Download only videos suitable for the given age'
complete --command yt-dlp --long-option download-archive --description 'Download only videos not listed in the archive file. Record the IDs of all downloaded videos in it' --require-parameter
complete --command yt-dlp --long-option no-download-archive --description 'Do not use archive file (default)'
complete --command yt-dlp --long-option max-downloads --description 'Abort after downloading NUMBER files'
complete --command yt-dlp --long-option break-on-existing --description 'Stop the download process when encountering a file that is in the archive supplied with the --download-archive option'
complete --command yt-dlp --long-option no-break-on-existing --description 'Do not stop the download process when encountering a file that is in the archive (default)'
complete --command yt-dlp --long-option break-on-reject
complete --command yt-dlp --long-option break-per-input --description 'Alters --max-downloads, --break-on-existing, --break-match-filters, and autonumber to reset per input URL'
complete --command yt-dlp --long-option no-break-per-input --description '--break-on-existing and similar options terminates the entire download queue'
complete --command yt-dlp --long-option skip-playlist-after-errors --description 'Number of allowed failures until the rest of the playlist is skipped'
complete --command yt-dlp --long-option include-ads
complete --command yt-dlp --long-option no-include-ads
complete --command yt-dlp --long-option concurrent-fragments --short-option N --description 'Number of fragments of a dash/hlsnative video that should be downloaded concurrently (default is %default)'
complete --command yt-dlp --long-option limit-rate --short-option r --description 'Maximum download rate in bytes per second, e.g. 50K or 4.2M'
complete --command yt-dlp --long-option throttled-rate --description 'Minimum download rate in bytes per second below which throttling is assumed and the video data is re-extracted, e.g. 100K'
complete --command yt-dlp --long-option retries --short-option R --description 'Number of retries (default is %default), or "infinite"'
complete --command yt-dlp --long-option file-access-retries --description 'Number of times to retry on file access error (default is %default), or "infinite"'
complete --command yt-dlp --long-option fragment-retries --description 'Number of retries for a fragment (default is %default), or "infinite" (DASH, hlsnative and ISM)'
complete --command yt-dlp --long-option retry-sleep --description 'Time to sleep between retries in seconds (optionally) prefixed by the type of retry (http (default), fragment, file_access, extractor) to apply the sleep to. EXPR can be a number, linear=START[:END[:STEP=1]] or exp=START[:END[:BASE=2]]. This option can be used multiple times to set the sleep for the different retry types, e.g. --retry-sleep linear=1::2 --retry-sleep fragment:exp=1:20'
complete --command yt-dlp --long-option skip-unavailable-fragments --description 'Skip unavailable fragments for DASH, hlsnative and ISM downloads (default) (Alias: --no-abort-on-unavailable-fragments)'
complete --command yt-dlp --long-option abort-on-unavailable-fragments --description 'Abort download if a fragment is unavailable (Alias: --no-skip-unavailable-fragments)'
complete --command yt-dlp --long-option keep-fragments --description 'Keep downloaded fragments on disk after downloading is finished'
complete --command yt-dlp --long-option no-keep-fragments --description 'Delete downloaded fragments after downloading is finished (default)'
complete --command yt-dlp --long-option buffer-size --description 'Size of download buffer, e.g. 1024 or 16K (default is %default)'
complete --command yt-dlp --long-option resize-buffer --description 'The buffer size is automatically resized from an initial value of --buffer-size (default)'
complete --command yt-dlp --long-option no-resize-buffer --description 'Do not automatically adjust the buffer size'
complete --command yt-dlp --long-option http-chunk-size --description 'Size of a chunk for chunk-based HTTP downloading, e.g. 10485760 or 10M (default is disabled). May be useful for bypassing bandwidth throttling imposed by a webserver (experimental)'
complete --command yt-dlp --long-option test
complete --command yt-dlp --long-option playlist-reverse
complete --command yt-dlp --long-option no-playlist-reverse
complete --command yt-dlp --long-option playlist-random --description 'Download playlist videos in random order'
complete --command yt-dlp --long-option lazy-playlist --description 'Process entries in the playlist as they are received. This disables n_entries, --playlist-random and --playlist-reverse'
complete --command yt-dlp --long-option no-lazy-playlist --description 'Process videos in the playlist only after the entire playlist is parsed (default)'
complete --command yt-dlp --long-option xattr-set-filesize --description 'Set file xattribute ytdl.filesize with expected file size'
complete --command yt-dlp --long-option hls-prefer-native
complete --command yt-dlp --long-option hls-prefer-ffmpeg
complete --command yt-dlp --long-option hls-use-mpegts --description 'Use the mpegts container for HLS videos; allowing some players to play the video while downloading, and reducing the chance of file corruption if download is interrupted. This is enabled by default for live streams'
complete --command yt-dlp --long-option no-hls-use-mpegts --description 'Do not use the mpegts container for HLS videos. This is default when not downloading live streams'
complete --command yt-dlp --long-option download-sections --description 'Download only chapters that match the regular expression. A "*" prefix denotes time-range instead of chapter. Negative timestamps are calculated from the end. "*from-url" can be used to download between the "start_time" and "end_time" extracted from the URL. Needs ffmpeg. This option can be used multiple times to download multiple sections, e.g. --download-sections "*10:15-inf" --download-sections "intro"'
complete --command yt-dlp --long-option downloader --description 'Name or path of the external downloader to use (optionally) prefixed by the protocols (http, ftp, m3u8, dash, rstp, rtmp, mms) to use it for. Currently supports native, aria2c, avconv, axel, curl, ffmpeg, httpie, wget. You can use this option multiple times to set different downloaders for different protocols. E.g. --downloader aria2c --downloader "dash,m3u8:native" will use aria2c for http/ftp downloads, and the native downloader for dash/m3u8 downloads (Alias: --external-downloader)'
complete --command yt-dlp --long-option downloader-args --description 'Give these arguments to the external downloader. Specify the downloader name and the arguments separated by a colon ":". For ffmpeg, arguments can be passed to different positions using the same syntax as --postprocessor-args. You can use this option multiple times to give different arguments to different downloaders (Alias: --external-downloader-args)'
complete --command yt-dlp --long-option batch-file --short-option a --description 'File containing URLs to download ("-" for stdin), one URL per line. Lines starting with "#", ";" or "]" are considered as comments and ignored' --require-parameter
complete --command yt-dlp --long-option no-batch-file --description 'Do not read URLs from batch file (default)'
complete --command yt-dlp --long-option id
complete --command yt-dlp --long-option paths --short-option P --description 'The paths where the files should be downloaded. Specify the type of file and the path separated by a colon ":". All the same TYPES as --output are supported. Additionally, you can also provide "home" (default) and "temp" paths. All intermediary files are first downloaded to the temp path and then the final files are moved over to the home path after download is finished. This option is ignored if --output is an absolute path'
complete --command yt-dlp --long-option output --short-option o --description 'Output filename template; see "OUTPUT TEMPLATE" for details'
complete --command yt-dlp --long-option output-na-placeholder --description 'Placeholder for unavailable fields in --output (default: "%default")'
complete --command yt-dlp --long-option autonumber-size
complete --command yt-dlp --long-option autonumber-start
complete --command yt-dlp --long-option restrict-filenames --description 'Restrict filenames to only ASCII characters, and avoid "&" and spaces in filenames'
complete --command yt-dlp --long-option no-restrict-filenames --description 'Allow Unicode characters, "&" and spaces in filenames (default)'
complete --command yt-dlp --long-option windows-filenames --description 'Force filenames to be Windows-compatible'
complete --command yt-dlp --long-option no-windows-filenames --description 'Sanitize filenames only minimally'
complete --command yt-dlp --long-option trim-filenames --description 'Limit the filename length (excluding extension) to the specified number of characters'
complete --command yt-dlp --long-option no-overwrites --short-option w --description 'Do not overwrite any files'
complete --command yt-dlp --long-option force-overwrites --description 'Overwrite all video and metadata files. This option includes --no-continue'
complete --command yt-dlp --long-option no-force-overwrites --description 'Do not overwrite the video, but overwrite related files (default)'
complete --command yt-dlp --long-option continue --short-option c --description 'Resume partially downloaded files/fragments (default)'
complete --command yt-dlp --long-option no-continue --description 'Do not resume partially downloaded fragments. If the file is not fragmented, restart download of the entire file'
complete --command yt-dlp --long-option part --description 'Use .part files instead of writing directly into output file (default)'
complete --command yt-dlp --long-option no-part --description 'Do not use .part files - write directly into output file'
complete --command yt-dlp --long-option mtime --description 'Use the Last-modified header to set the file modification time'
complete --command yt-dlp --long-option no-mtime --description 'Do not use the Last-modified header to set the file modification time (default)'
complete --command yt-dlp --long-option write-description --description 'Write video description to a .description file'
complete --command yt-dlp --long-option no-write-description --description 'Do not write video description (default)'
complete --command yt-dlp --long-option write-info-json --description 'Write video metadata to a .info.json file (this may contain personal information)'
complete --command yt-dlp --long-option no-write-info-json --description 'Do not write video metadata (default)'
complete --command yt-dlp --long-option write-annotations
complete --command yt-dlp --long-option no-write-annotations
complete --command yt-dlp --long-option write-playlist-metafiles --description 'Write playlist metadata in addition to the video metadata when using --write-info-json, --write-description etc. (default)'
complete --command yt-dlp --long-option no-write-playlist-metafiles --description 'Do not write playlist metadata when using --write-info-json, --write-description etc.'
complete --command yt-dlp --long-option clean-info-json --description 'Remove some internal metadata such as filenames from the infojson (default)'
complete --command yt-dlp --long-option no-clean-info-json --description 'Write all fields to the infojson'
complete --command yt-dlp --long-option write-comments --description 'Retrieve video comments to be placed in the infojson. The comments are fetched even without this option if the extraction is known to be quick (Alias: --get-comments)'
complete --command yt-dlp --long-option no-write-comments --description 'Do not retrieve video comments unless the extraction is known to be quick (Alias: --no-get-comments)'
complete --command yt-dlp --long-option load-info-json --description 'JSON file containing the video information (created with the "--write-info-json" option)'
complete --command yt-dlp --long-option cookies --description 'Netscape formatted file to read cookies from and dump cookie jar in' --require-parameter
complete --command yt-dlp --long-option no-cookies --description 'Do not read/dump cookies from/to file (default)'
complete --command yt-dlp --long-option cookies-from-browser --description 'The name of the browser to load cookies from. Currently supported browsers are: brave, chrome, chromium, edge, firefox, opera, safari, vivaldi, whale. Optionally, the KEYRING used for decrypting Chromium cookies on Linux, the name/path of the PROFILE to load cookies from, and the CONTAINER name (if Firefox) ("none" for no container) can be given with their respective separators. By default, all containers of the most recently accessed profile are used. Currently supported keyrings are: basictext, gnomekeyring, kwallet, kwallet5, kwallet6'
complete --command yt-dlp --long-option no-cookies-from-browser --description 'Do not load cookies from browser (default)'
complete --command yt-dlp --long-option cache-dir --description 'Location in the filesystem where yt-dlp can store some downloaded information (such as client ids and signatures) permanently. By default ${XDG_CACHE_HOME}/yt-dlp'
complete --command yt-dlp --long-option no-cache-dir --description 'Disable filesystem caching'
complete --command yt-dlp --long-option rm-cache-dir --description 'Delete all filesystem cache files'
complete --command yt-dlp --long-option write-thumbnail --description 'Write thumbnail image to disk'
complete --command yt-dlp --long-option no-write-thumbnail --description 'Do not write thumbnail image to disk (default)'
complete --command yt-dlp --long-option write-all-thumbnails --description 'Write all thumbnail image formats to disk'
complete --command yt-dlp --long-option list-thumbnails --description 'List available thumbnails of each video. Simulate unless --no-simulate is used'
complete --command yt-dlp --long-option write-link --description 'Write an internet shortcut file, depending on the current platform (.url, .webloc or .desktop). The URL may be cached by the OS'
complete --command yt-dlp --long-option write-url-link --description 'Write a .url Windows internet shortcut. The OS caches the URL based on the file path'
complete --command yt-dlp --long-option write-webloc-link --description 'Write a .webloc macOS internet shortcut'
complete --command yt-dlp --long-option write-desktop-link --description 'Write a .desktop Linux internet shortcut'
complete --command yt-dlp --long-option quiet --short-option q --description 'Activate quiet mode. If used with --verbose, print the log to stderr'
complete --command yt-dlp --long-option no-quiet --description 'Deactivate quiet mode. (Default)'
complete --command yt-dlp --long-option no-warnings --description 'Ignore warnings'
complete --command yt-dlp --long-option simulate --short-option s --description 'Do not download the video and do not write anything to disk'
complete --command yt-dlp --long-option no-simulate --description 'Download the video even if printing/listing options are used'
complete --command yt-dlp --long-option ignore-no-formats-error --description 'Ignore "No video formats" error. Useful for extracting metadata even if the videos are not actually available for download (experimental)'
complete --command yt-dlp --long-option no-ignore-no-formats-error --description 'Throw error when no downloadable video formats are found (default)'
complete --command yt-dlp --long-option skip-download --description 'Do not download the video but write all related files (Alias: --no-download)'
complete --command yt-dlp --long-option print --short-option O --description 'Field name or output template to print to screen, optionally prefixed with when to print it, separated by a ":". Supported values of "WHEN" are the same as that of --use-postprocessor (default: video). Implies --quiet. Implies --simulate unless --no-simulate or later stages of WHEN are used. This option can be used multiple times'
complete --command yt-dlp --long-option print-to-file --description 'Append given template to the file. The values of WHEN and TEMPLATE are the same as that of --print. FILE uses the same syntax as the output template. This option can be used multiple times'
complete --command yt-dlp --long-option get-url --short-option g
complete --command yt-dlp --long-option get-title --short-option e
complete --command yt-dlp --long-option get-id
complete --command yt-dlp --long-option get-thumbnail
complete --command yt-dlp --long-option get-description
complete --command yt-dlp --long-option get-duration
complete --command yt-dlp --long-option get-filename
complete --command yt-dlp --long-option get-format
complete --command yt-dlp --long-option dump-json --short-option j --description 'Quiet, but print JSON information for each video. Simulate unless --no-simulate is used. See "OUTPUT TEMPLATE" for a description of available keys'
complete --command yt-dlp --long-option dump-single-json --short-option J --description 'Quiet, but print JSON information for each URL or infojson passed. Simulate unless --no-simulate is used. If the URL refers to a playlist, the whole playlist information is dumped in a single line'
complete --command yt-dlp --long-option print-json
complete --command yt-dlp --long-option force-write-archive --description 'Force download archive entries to be written as far as no errors occur, even if -s or another simulation option is used (Alias: --force-download-archive)'
complete --command yt-dlp --long-option newline --description 'Output progress bar as new lines'
complete --command yt-dlp --long-option no-progress --description 'Do not print progress bar'
complete --command yt-dlp --long-option progress --description 'Show progress bar, even if in quiet mode'
complete --command yt-dlp --long-option console-title --description 'Display progress in console titlebar'
complete --command yt-dlp --long-option progress-template --description 'Template for progress outputs, optionally prefixed with one of "download:" (default), "download-title:" (the console title), "postprocess:",  or "postprocess-title:". The video'"'"'s fields are accessible under the "info" key and the progress attributes are accessible under "progress" key. E.g. --console-title --progress-template "download-title:%(info.id)s-%(progress.eta)s"'
complete --command yt-dlp --long-option progress-delta --description 'Time between progress output (default: 0)'
complete --command yt-dlp --long-option verbose --short-option v --description 'Print various debugging information'
complete --command yt-dlp --long-option dump-pages --description 'Print downloaded pages encoded using base64 to debug problems (very verbose)'
complete --command yt-dlp --long-option write-pages --description 'Write downloaded intermediary pages to files in the current directory to debug problems'
complete --command yt-dlp --long-option load-pages
complete --command yt-dlp --long-option youtube-print-sig-code
complete --command yt-dlp --long-option print-traffic --description 'Display sent and read HTTP traffic'
complete --command yt-dlp --long-option call-home --short-option C
complete --command yt-dlp --long-option no-call-home
complete --command yt-dlp --long-option encoding --description 'Force the specified encoding (experimental)'
complete --command yt-dlp --long-option legacy-server-connect --description 'Explicitly allow HTTPS connection to servers that do not support RFC 5746 secure renegotiation'
complete --command yt-dlp --long-option no-check-certificates --description 'Suppress HTTPS certificate validation'
complete --command yt-dlp --long-option prefer-insecure --description 'Use an unencrypted connection to retrieve information about the video (Currently supported only for YouTube)'
complete --command yt-dlp --long-option user-agent
complete --command yt-dlp --long-option referer
complete --command yt-dlp --long-option add-headers --description 'Specify a custom HTTP header and its value, separated by a colon ":". You can use this option multiple times'
complete --command yt-dlp --long-option bidi-workaround --description 'Work around terminals that lack bidirectional text support. Requires bidiv or fribidi executable in PATH'
complete --command yt-dlp --long-option sleep-requests --description 'Number of seconds to sleep between requests during data extraction'
complete --command yt-dlp --long-option sleep-interval --description 'Number of seconds to sleep before each download. This is the minimum time to sleep when used along with --max-sleep-interval (Alias: --min-sleep-interval)'
complete --command yt-dlp --long-option max-sleep-interval --description 'Maximum number of seconds to sleep. Can only be used along with --min-sleep-interval'
complete --command yt-dlp --long-option sleep-subtitles --description 'Number of seconds to sleep before each subtitle download'
complete --command yt-dlp --long-option format --short-option f --description 'Video format code, see "FORMAT SELECTION" for more details'
complete --command yt-dlp --long-option format-sort --short-option S --description 'Sort the formats by the fields given, see "Sorting Formats" for more details'
complete --command yt-dlp --long-option format-sort-force --description 'Force user specified sort order to have precedence over all fields, see "Sorting Formats" for more details (Alias: --S-force)'
complete --command yt-dlp --long-option no-format-sort-force --description 'Some fields have precedence over the user specified sort order (default)'
complete --command yt-dlp --long-option video-multistreams --description 'Allow multiple video streams to be merged into a single file'
complete --command yt-dlp --long-option no-video-multistreams --description 'Only one video stream is downloaded for each output file (default)'
complete --command yt-dlp --long-option audio-multistreams --description 'Allow multiple audio streams to be merged into a single file'
complete --command yt-dlp --long-option no-audio-multistreams --description 'Only one audio stream is downloaded for each output file (default)'
complete --command yt-dlp --long-option all-formats
complete --command yt-dlp --long-option prefer-free-formats --description 'Prefer video formats with free containers over non-free ones of the same quality. Use with "-S ext" to strictly prefer free containers irrespective of quality'
complete --command yt-dlp --long-option no-prefer-free-formats --description 'Don'"'"'t give any special preference to free containers (default)'
complete --command yt-dlp --long-option check-formats --description 'Make sure formats are selected only from those that are actually downloadable'
complete --command yt-dlp --long-option check-all-formats --description 'Check all formats for whether they are actually downloadable'
complete --command yt-dlp --long-option no-check-formats --description 'Do not check that the formats are actually downloadable'
complete --command yt-dlp --long-option list-formats --short-option F --description 'List available formats of each video. Simulate unless --no-simulate is used'
complete --command yt-dlp --long-option list-formats-as-table
complete --command yt-dlp --long-option list-formats-old
complete --command yt-dlp --long-option merge-output-format --description 'Containers that may be used when merging formats, separated by "/", e.g. "mp4/mkv". Ignored if no merge is required. (currently supported: avi, flv, mkv, mov, mp4, webm)'
complete --command yt-dlp --long-option allow-unplayable-formats
complete --command yt-dlp --long-option no-allow-unplayable-formats
complete --command yt-dlp --long-option write-subs --description 'Write subtitle file'
complete --command yt-dlp --long-option no-write-subs --description 'Do not write subtitle file (default)'
complete --command yt-dlp --long-option write-auto-subs --description 'Write automatically generated subtitle file (Alias: --write-automatic-subs)'
complete --command yt-dlp --long-option no-write-auto-subs --description 'Do not write auto-generated subtitles (default) (Alias: --no-write-automatic-subs)'
complete --command yt-dlp --long-option all-subs
complete --command yt-dlp --long-option list-subs --description 'List available subtitles of each video. Simulate unless --no-simulate is used'
complete --command yt-dlp --long-option sub-format --description 'Subtitle format; accepts formats preference separated by "/", e.g. "srt" or "ass/srt/best"'
complete --command yt-dlp --long-option sub-langs --description 'Languages of the subtitles to download (can be regex) or "all" separated by commas, e.g. --sub-langs "en.*,ja" (where "en.*" is a regex pattern that matches "en" followed by 0 or more of any character). You can prefix the language code with a "-" to exclude it from the requested languages, e.g. --sub-langs all,-live_chat. Use --list-subs for a list of available language tags'
complete --command yt-dlp --long-option username --short-option u --description 'Login with this account ID'
complete --command yt-dlp --long-option password --short-option p --description 'Account password. If this option is left out, yt-dlp will ask interactively'
complete --command yt-dlp --long-option twofactor --short-option 2 --description 'Two-factor authentication code'
complete --command yt-dlp --long-option netrc --short-option n --description 'Use .netrc authentication data'
complete --command yt-dlp --long-option netrc-location --description 'Location of .netrc authentication data; either the path or its containing directory. Defaults to ~/.netrc'
complete --command yt-dlp --long-option netrc-cmd --description 'Command to execute to get the credentials for an extractor.'
complete --command yt-dlp --long-option video-password --description 'Video-specific password'
complete --command yt-dlp --long-option ap-mso --description 'Adobe Pass multiple-system operator (TV provider) identifier, use --ap-list-mso for a list of available MSOs'
complete --command yt-dlp --long-option ap-username --description 'Multiple-system operator account login'
complete --command yt-dlp --long-option ap-password --description 'Multiple-system operator account password. If this option is left out, yt-dlp will ask interactively'
complete --command yt-dlp --long-option ap-list-mso --description 'List all supported multiple-system operators'
complete --command yt-dlp --long-option client-certificate --description 'Path to client certificate file in PEM format. May include the private key'
complete --command yt-dlp --long-option client-certificate-key --description 'Path to private key file for client certificate'
complete --command yt-dlp --long-option client-certificate-password --description 'Password for client certificate private key, if encrypted. If not provided, and the key is encrypted, yt-dlp will ask interactively'
complete --command yt-dlp --long-option extract-audio --short-option x --description 'Convert video files to audio-only files (requires ffmpeg and ffprobe)'
complete --command yt-dlp --long-option audio-format --description 'Format to convert the audio to when -x is used. (currently supported: best (default), aac, alac, flac, m4a, mp3, opus, vorbis, wav). You can specify multiple rules using similar syntax as --remux-video'
complete --command yt-dlp --long-option audio-quality --description 'Specify ffmpeg audio quality to use when converting the audio with -x. Insert a value between 0 (best) and 10 (worst) for VBR or a specific bitrate like 128K (default %default)'
complete --command yt-dlp --long-option remux-video --description 'Remux the video into another container if necessary (currently supported: avi, flv, gif, mkv, mov, mp4, webm, aac, aiff, alac, flac, m4a, mka, mp3, ogg, opus, vorbis, wav). If the target container does not support the video/audio codec, remuxing will fail. You can specify multiple rules; e.g. "aac>m4a/mov>mp4/mkv" will remux aac to m4a, mov to mp4 and anything else to mkv' --arguments 'mp4 mkv' --exclusive
complete --command yt-dlp --long-option recode-video --description 'Re-encode the video into another format if necessary. The syntax and supported formats are the same as --remux-video' --arguments 'mp4 flv ogg webm mkv' --exclusive
complete --command yt-dlp --long-option postprocessor-args --description 'Give these arguments to the postprocessors. Specify the postprocessor/executable name and the arguments separated by a colon ":" to give the argument to the specified postprocessor/executable. Supported PP are: Merger, ModifyChapters, SplitChapters, ExtractAudio, VideoRemuxer, VideoConvertor, Metadata, EmbedSubtitle, EmbedThumbnail, SubtitlesConvertor, ThumbnailsConvertor, FixupStretched, FixupM4a, FixupM3u8, FixupTimestamp and FixupDuration. The supported executables are: AtomicParsley, FFmpeg and FFprobe. You can also specify "PP+EXE:ARGS" to give the arguments to the specified executable only when being used by the specified postprocessor. Additionally, for ffmpeg/ffprobe, "_i"/"_o" can be appended to the prefix optionally followed by a number to pass the argument before the specified input/output file, e.g. --ppa "Merger+ffmpeg_i1:-v quiet". You can use this option multiple times to give different arguments to different postprocessors. (Alias: --ppa)'
complete --command yt-dlp --long-option keep-video --short-option k --description 'Keep the intermediate video file on disk after post-processing'
complete --command yt-dlp --long-option no-keep-video --description 'Delete the intermediate video file after post-processing (default)'
complete --command yt-dlp --long-option post-overwrites --description 'Overwrite post-processed files (default)'
complete --command yt-dlp --long-option no-post-overwrites --description 'Do not overwrite post-processed files'
complete --command yt-dlp --long-option embed-subs --description 'Embed subtitles in the video (only for mp4, webm and mkv videos)'
complete --command yt-dlp --long-option no-embed-subs --description 'Do not embed subtitles (default)'
complete --command yt-dlp --long-option embed-thumbnail --description 'Embed thumbnail in the video as cover art'
complete --command yt-dlp --long-option no-embed-thumbnail --description 'Do not embed thumbnail (default)'
complete --command yt-dlp --long-option embed-metadata --description 'Embed metadata to the video file. Also embeds chapters/infojson if present unless --no-embed-chapters/--no-embed-info-json are used (Alias: --add-metadata)'
complete --command yt-dlp --long-option no-embed-metadata --description 'Do not add metadata to file (default) (Alias: --no-add-metadata)'
complete --command yt-dlp --long-option embed-chapters --description 'Add chapter markers to the video file (Alias: --add-chapters)'
complete --command yt-dlp --long-option no-embed-chapters --description 'Do not add chapter markers (default) (Alias: --no-add-chapters)'
complete --command yt-dlp --long-option embed-info-json --description 'Embed the infojson as an attachment to mkv/mka video files'
complete --command yt-dlp --long-option no-embed-info-json --description 'Do not embed the infojson as an attachment to the video file'
complete --command yt-dlp --long-option metadata-from-title
complete --command yt-dlp --long-option parse-metadata --description 'Parse additional metadata like title/artist from other fields; see "MODIFYING METADATA" for details. Supported values of "WHEN" are the same as that of --use-postprocessor (default: pre_process)'
complete --command yt-dlp --long-option replace-in-metadata --description 'Replace text in a metadata field using the given regex. This option can be used multiple times. Supported values of "WHEN" are the same as that of --use-postprocessor (default: pre_process)'
complete --command yt-dlp --long-option xattrs --description 'Write metadata to the video file'"'"'s xattrs (using Dublin Core and XDG standards)'
complete --command yt-dlp --long-option concat-playlist --description 'Concatenate videos in a playlist. One of "never", "always", or "multi_video" (default; only when the videos form a single show). All the video files must have the same codecs and number of streams to be concatenable. The "pl_video:" prefix can be used with "--paths" and "--output" to set the output filename for the concatenated files. See "OUTPUT TEMPLATE" for details'
complete --command yt-dlp --long-option fixup --description 'Automatically correct known faults of the file. One of never (do nothing), warn (only emit a warning), detect_or_warn (the default; fix the file if we can, warn otherwise), force (try fixing even if the file already exists)'
complete --command yt-dlp --long-option prefer-avconv
complete --command yt-dlp --long-option prefer-ffmpeg
complete --command yt-dlp --long-option ffmpeg-location --description 'Location of the ffmpeg binary; either the path to the binary or its containing directory'
complete --command yt-dlp --long-option exec --description 'Execute a command, optionally prefixed with when to execute it, separated by a ":". Supported values of "WHEN" are the same as that of --use-postprocessor (default: after_move). The same syntax as the output template can be used to pass any field as arguments to the command. If no fields are passed, %(filepath,_filename|)q is appended to the end of the command. This option can be used multiple times'
complete --command yt-dlp --long-option no-exec --description 'Remove any previously defined --exec'
complete --command yt-dlp --long-option exec-before-download
complete --command yt-dlp --long-option no-exec-before-download
complete --command yt-dlp --long-option convert-subs --description 'Convert the subtitles to another format (currently supported: ass, lrc, srt, vtt). Use "--convert-subs none" to disable conversion (default) (Alias: --convert-subtitles)'
complete --command yt-dlp --long-option convert-thumbnails --description 'Convert the thumbnails to another format (currently supported: jpg, png, webp). You can specify multiple rules using similar syntax as "--remux-video". Use "--convert-thumbnails none" to disable conversion (default)'
complete --command yt-dlp --long-option split-chapters --description 'Split video into multiple files based on internal chapters. The "chapter:" prefix can be used with "--paths" and "--output" to set the output filename for the split files. See "OUTPUT TEMPLATE" for details'
complete --command yt-dlp --long-option no-split-chapters --description 'Do not split video based on chapters (default)'
complete --command yt-dlp --long-option remove-chapters --description 'Remove chapters whose title matches the given regular expression. The syntax is the same as --download-sections. This option can be used multiple times'
complete --command yt-dlp --long-option no-remove-chapters --description 'Do not remove any chapters from the file (default)'
complete --command yt-dlp --long-option force-keyframes-at-cuts --description 'Force keyframes at cuts when downloading/splitting/removing sections. This is slow due to needing a re-encode, but the resulting video may have fewer artifacts around the cuts'
complete --command yt-dlp --long-option no-force-keyframes-at-cuts --description 'Do not force keyframes around the chapters when cutting/splitting (default)'
complete --command yt-dlp --long-option use-postprocessor --description 'The (case-sensitive) name of plugin postprocessors to be enabled, and (optionally) arguments to be passed to it, separated by a colon ":". ARGS are a semicolon ";" delimited list of NAME=VALUE. The "when" argument determines when the postprocessor is invoked. It can be one of "pre_process" (after video extraction), "after_filter" (after video passes filter), "video" (after --format; before --print/--output), "before_dl" (before each video download), "post_process" (after each video download; default), "after_move" (after moving the video file to its final location), "after_video" (after downloading and processing all formats of a video), or "playlist" (at end of playlist). This option can be used multiple times to add different postprocessors'
complete --command yt-dlp --long-option sponsorblock-mark --description 'SponsorBlock categories to create chapters for, separated by commas. Available categories are sponsor, intro, outro, selfpromo, preview, filler, interaction, music_offtopic, poi_highlight, chapter, all and default (=all). You can prefix the category with a "-" to exclude it. See [1] for descriptions of the categories. E.g. --sponsorblock-mark all,-preview [1] https://wiki.sponsor.ajay.app/w/Segment_Categories'
complete --command yt-dlp --long-option sponsorblock-remove --description 'SponsorBlock categories to be removed from the video file, separated by commas. If a category is present in both mark and remove, remove takes precedence. The syntax and available categories are the same as for --sponsorblock-mark except that "default" refers to "all,-filler" and poi_highlight, chapter are not available'
complete --command yt-dlp --long-option sponsorblock-chapter-title --description 'An output template for the title of the SponsorBlock chapters created by --sponsorblock-mark. The only available fields are start_time, end_time, category, categories, name, category_names. Defaults to "%default"'
complete --command yt-dlp --long-option no-sponsorblock --description 'Disable both --sponsorblock-mark and --sponsorblock-remove'
complete --command yt-dlp --long-option sponsorblock-api --description 'SponsorBlock API location, defaults to %default'
complete --command yt-dlp --long-option sponskrub
complete --command yt-dlp --long-option no-sponskrub
complete --command yt-dlp --long-option sponskrub-cut
complete --command yt-dlp --long-option no-sponskrub-cut
complete --command yt-dlp --long-option sponskrub-force
complete --command yt-dlp --long-option no-sponskrub-force
complete --command yt-dlp --long-option sponskrub-location
complete --command yt-dlp --long-option sponskrub-args
complete --command yt-dlp --long-option extractor-retries --description 'Number of retries for known extractor errors (default is %default), or "infinite"'
complete --command yt-dlp --long-option allow-dynamic-mpd --description 'Process dynamic DASH manifests (default) (Alias: --no-ignore-dynamic-mpd)'
complete --command yt-dlp --long-option ignore-dynamic-mpd --description 'Do not process dynamic DASH manifests (Alias: --no-allow-dynamic-mpd)'
complete --command yt-dlp --long-option hls-split-discontinuity --description 'Split HLS playlists to different formats at discontinuities such as ad breaks'
complete --command yt-dlp --long-option no-hls-split-discontinuity --description 'Do not split HLS playlists into different formats at discontinuities such as ad breaks (default)'
complete --command yt-dlp --long-option extractor-args --description 'Pass ARGS arguments to the IE_KEY extractor. See "EXTRACTOR ARGUMENTS" for details. You can use this option multiple times to give arguments for different extractors'
complete --command yt-dlp --long-option youtube-include-dash-manifest
complete --command yt-dlp --long-option youtube-skip-dash-manifest
complete --command yt-dlp --long-option youtube-include-hls-manifest
complete --command yt-dlp --long-option youtube-skip-hls-manifest


complete --command yt-dlp --arguments ":ytfavorites :ytrecommended :ytsubscriptions :ytwatchlater :ythistory"
