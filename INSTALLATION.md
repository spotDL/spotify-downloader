

# spotDL Installation Guide:

spotDL is a free and open-source tool that fetches your Spotify playlist and downloads.



To start downloading type :



`spotDL [spotify album/song/playlist url]`



Also, spotDL can queue links, query searches, playlists, etc. To queue links, separate them with space.

Example: `spotDL link1 link2`

![Link queue](https://i.hizliresim.com/Q6E2jv.png)



To install and use spotDL, you will need :



**Python (added to PATH)**

**FFmpeg (added to PATH)**



For Python be sure that you selected the '**add to path**' option while installing Python.



For FFmpeg, if you are not sure how to add FFmpeg to the path you can read this tutorial: 

blog.gregzaal.com/how-to-install-FFmpeg-on-windows/



For FFmpeg be sure you place the FFmpeg folder somewhere you won't lose or delete it ( We recommend putting the FFmpeg folder to the system disk) and adding the “FFmpeg/bin” folder to the PATH.



After everything is done, type **python** and **FFmpeg** to check versions.

If you did install and added FFmpeg and Python to PATH correctly, you should get these messages as outputs :

![FFpmeg output](https://i.hizliresim.com/hXUCLr.png)



![Python output](https://i.hizliresim.com/CW8lba.png)



Be sure that you type these commands in separate windows.



Now it's time to installing spotDL:



**



# Instaling spotDL:

**



To download from the master, type :



`pip install https://codeload.github.com/spotDL/spotify-downloader/zip/master` 

in the terminal.



Master is a stable version of spotDL. We recommend using master if you are not experiencing any problems.



If you have some issues with master and you want to download from hotfix, type: 



`pip install https://codeload.github.com/spotDL/spotify-downloader/zip/hotfix`

 in the terminal.



Before switching to versions, ***(if you already installed spotDL before)*** you should make a clean install. 



## CLEAN INSTALL FROM MASTER:

`pip install pip-autoremove` 

`pip-autoremove spotDL` 

`pip cache purge` 

`pip install https://codeload.github.com/spotDL/spotify-downloader/zip/master`

`spotDL [trackUrl]`



## **CLEAN INSTALL FROM HOTFIX:**

`pip install pip-autoremove`

`pip-autoremove spotdl`

`pip cache purge`

`pip install https://codeload.github.com/spotDL/spotify-downloader/zip/hotfix`

`spotdl [trackUrl]`

Select your desired version to install and try if you installed spotDL correctly:



Type **spotDL** and see if the command line does see spotDL as a command. If it does not, check again.

![spotDL output](https://i.hizliresim.com/ikbcd4.png)



# But where do spotDL download songs?



spotDL will download songs to where you did run cmd/Powershell



In this example, we ran spotDL from cmd in Users/ Administrator

![spotDL downloading song](https://i.hizliresim.com/rEjeWK.png)

And spotDL did download song to:

![spotDL downloaded songs](https://i.hizliresim.com/5pYEBd.png)

Administrator folder. 



To change the directory of the downloaded songs, you have to open cmd/Powershell from a different folder.



Create a folder or use your existing folder. (it can be whatever folder you want).

Then click the address bar of your folder.

![Selecting folder address bar](https://i.hizliresim.com/jAMOQr.png)

Type **cmd** or **Powershell** to address bar of your folder.

![Type cmd in address bar](https://i.hizliresim.com/xWnnPI.png)





And now it runs in your folder. Your downloaded songs will be here.

![spotDl working on a different folder](https://i.hizliresim.com/PtgLGG.png)



# Bug report :

To report issues, open an issue to spotDL GitHub: [github.com/spotDL/spotify-downloader/issues]()



# Discord:

For support, you can join to spotDL Discord server: [discord.gg/AXypWnTp92]()



NoSubwayzz from spotDl team