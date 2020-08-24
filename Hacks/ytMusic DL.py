from pytube import YouTube

def download(link, folder):
  yt=YouTube(link)
  t=yt.streams.filter(only_audio=True).all()
  t[0].download(folder)   # downloads only audio as a '.mp4' file,
                          # no clue why this weird behavior