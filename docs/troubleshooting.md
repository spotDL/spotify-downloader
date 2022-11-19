# Troubleshooting / FAQ Guide

As common issues or questions are encountered solutions will be added to this guide.

??? "'spotdl' is not recognized"

    Python/(site packages) is not added to PATH correctly. You need to install Python from
    <https://www.python.org/downloads/>

    Or you are using python from microsoft store. If so uninstall it and restart cmd. If this
    doesn't work reinstall python.

    ### Error message

    ```
    'spotdl' is not recognized as an internal or external command,
    operable program or batch file.
    ```

    ### Solution

    Ensure to add to PATH when installing: ![python install](https://i.imgur.com/jWq5EnV.png)

??? "spotdl: command not found"

    If you see this error after installing spotdl, that means that the bin (Binaries) folder is not
    on `$PATH`

    ### Solution

    #### `.bashrc`

    Add `export PATH=~/.local/bin:$PATH` at the bottom of `~/.bashrc`

    Then run `source ~/.bashrc`

    #### `.zshrc`

    Add `export PATH=~/.local/bin:$PATH` at the bottom of `~/.zshrc` Then run `source ~/.zshrc`

??? "pkg_resources.DistributionNotFound"

    Sometimes not all packages are installed but are required by yt-dlp for example: `brotli` or
    `websockets`

    ### Error Message

    `pkg_resources.DistributionNotFound: The 'websockets' distribution was not found and is required by yt-dlp`

    ### Solution

    `pip install brotli websockets yt-dlp -U`

??? "HTTP Error 404"

    <https://github.com/plamere/spotipy/issues/795#issuecomment-1100321148>

    ### Error Message

    `HTTP Error for GET to URL with Params: {} returned 404 due to None`

    ### Solution

    Update spotdl to the latest version which contains workaround.

    `pip install -U spotdl`

??? "ssl.SSLError: \[SSL: CERTIFICATE_VERIFY_FAILED\]"

    <https://stackoverflow.com/questions/27835619/urllib-and-ssl-certificate-verify-failed-error>

    ### Error Message

    `urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:847)>`

    ### Solution

    <https://stackoverflow.com/questions/27835619/urllib-and-ssl-certificate-verify-failed-error>

??? "RecursionError"

    <https://github.com/spotDL/spotify-downloader/issues/1493>

    ### Error Message

    `RecursionError: maximum recursion depth exceeded`

    ### Solution

    Update spotdl

    `pip install spotdl -U`

??? "RuntimeWarning"

    This happens when running spotdl using `python -m`.

    ### Error Message

    ```
    RuntimeWarning: 'spotdl.__main__' found in sys.modules after import of package 'spotdl',
    but prior to execution of 'spotdl.__main__'; this may result in unpredictable behaviour
    warn(RuntimeWarning(msg))
    ```

    ### Solution

    You can ignore this error or just run spotdl directly

??? "Not found '\_raw_ecb.so'"

    This error is specific for M1 Macs only.

    https://discord.com/channels/771628785447337985/871006150357823498
    https://discord.com/channels/771628785447337985/939475659238043738

    ### Error Message

    ```
    aise OSError("Cannot load native module '%s': %s" % (name, ", ".join(attempts)))
    OSError: Cannot load native module 'Cryptodome.Cipher._raw_ecb': Not found '_raw_ecb.cpython-39-darwin.so',
    Cannot load '_raw_ecb.abi3.so': dlopen(/opt/homebrew/lib/python3.9/site-packages/Cryptodome/Util/../Cipher/_raw_ecb.abi3.so, 6): no suitable image found.  Did find:
    /opt/homebrew/lib/python3.9/site-packages/Cryptodome/Util/../Cipher/_raw_ecb.abi3.so: mach-o, but wrong architecture
    /opt/homebrew/lib/python3.9/site-packages/Cryptodome/Cipher/_raw_ecb.abi3.so: mach-o, but wrong architecture, Not found '_raw_ecb.so'
    ```

    ### Solution

    Possible solutions:

    <https://discord.com/channels/771628785447337985/871006150357823498>
    <https://discord.com/channels/771628785447337985/939475659238043738>
