## SpotDL Installation Guide:

SpotDL is a free and open source tool for that fetchs your Spotify playlist and downloads.

To start downloading just type :

    **spotdl [spotify album/song/playlist url]**

Also spotdl can queue links, query searchs etc. Just separate them with space.

![enter image description here](https://i.hizliresim.com/Q6E2jv.png)

![enter image description here](https://i.hizliresim.com/9mRTNg.png)

To install and use spotDL , you will need :

Python (added to PATH)

ffmpeg (added to PATH)

All you have to do for Python is being sure that you selected "Add to PATH" option while Python installation.

If you don't know how to add programs to PATH you can read this tutorial.

For ffpmeg, you can read this tutorial: [http://blog.gregzaal.com/how-to-install-ffmpeg-on-windows/](http://blog.gregzaal.com/how-to-install-ffmpeg-on-windows/)

All you have to do for ffmpeg is placing ffpmeg folder that somewhere you won't lose or delete it (I recommend putting ffmpeg folder to system disk) , and adding "ffmpeg/bin" folder to the PATH.

If you did install and added ffpmeg and python correctly , you should get these messages:

Just simply type : python and ffpmeg to check versions

![enter image description here](https://i.hizliresim.com/CW8lba.png)

![enter image description here](https://i.hizliresim.com/hXUCLr.png)

Be sure that you type these in seperate windows.

Now its time to real deal, installing spotdl:

**

## Instaling spotdl:

**

To download from master , type :

	pip install [https://codeload.github.com/spotDL/spotify-downloader/zip/master](https://codeload.github.com/spotDL/spotify-downloader/zip/master)
in terminal.

Master is a stable version of spotDL. I recommend using master if you are not experiencing any problems.

Let's say you have some issues with master and you want download from hotfix :

	pip install [https://codeload.github.com/spotDL/spotify-downloader/zip/hotfix](https://codeload.github.com/spotDL/spotify-downloader/zip/hotfix)
in terminal.

Before swicthing to verisons , you should make a clean install (if you already installed spotdl before). To do this:

## CLEAN INSTALL FROM MASTER:

	 pip install pip-autoremove
	 pip-autoremove spotdl
	 pip cache purge
	 pip install [https://codeload.github.com/spotDL/spotify-downloader/zip/master](https://codeload.github.com/spotDL/spotify-downloader/zip/master)
	 spotdl [trackUrl]

Let's select our version to install and try if we installed spotDL correctly:

![enter image description here](https://i.hizliresim.com/ikbcd4.png)

Type : `spotdl` and see if it does see spotdl as a command. If it does not , check old steps again.

## But where it downloads?

spotDL will download songs to where you did run cmd/powershell

For an example i ran spotdl from cmd in Users/Administrator

![For an example i ran spotdl from cmd in Users/Administrator](https://i.hizliresim.com/qmpuQF.png)

And it downloaded song to:

![enter image description here](https://i.hizliresim.com/5pYEBd.png)

Administrator folder. Not a suprise.

*What if we want to download song to a different folder?*

In order to do that, you should open cmd/powershell from a different folder.

I created a folder and named it as spotdl (it can be whatever you want).

![enter image description here](https://i.hizliresim.com/jAMOQr.png)

Then click the adressbar of your folder.

![enter image description here](https://i.hizliresim.com/xWnnPI.png)

Type `cmd` or `powershell` to adress bar of your folder.

![enter image description here](https://i.hizliresim.com/PtgLGG.png)

And now it runs at our folder. Your downloaded songs will be here.

## Bug report :

To report issues , open a issue to spotDL GitHub:
[https://github.com/spotDL/spotify-downloader/issues](https://github.com/spotDL/spotify-downloader/issues)

## Discord:

For a support you can join to spotDL Discord server too:
[https://discord.gg/AXypWnTp92](https://discord.gg/AXypWnTp92)
