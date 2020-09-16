

from spotdl.cli.logger import NewProgressBar
from rich.progress import Progress, BarColumn, TimeRemainingColumn
from rich.progress import track
import time


def progresstest():
	# p1 = NewProgressBar('Song1')
	# for i in range(1, 100, 10):
	# 	# print(i)
	# 	p1.setProgress(i)
	# 	time.sleep(0.1)
	# p1.close()
	# style = "black on black"
	# progress = Progress(
	# 	"[progress.description]{task.description}",
	# 	BarColumn(bar_width=None),
	# 	"[progress.percentage]{task.percentage:>3.0f}%",
	# 	TimeRemainingColumn(),
	# )

	# for step in track(range(100), style="black on black", finished_style="white", description="[green]Processing..."):
		# time.sleep(0.1)

	# progress = Progress(
	# 	"[progress.description]{task.description}",
	# 	BarColumn(),
	# 	"[progress.percentage]{task.percentage:>3.0f}%",
	# 	TimeRemainingColumn(),
	# )

	with Progress(
		# "[progress.description]{task.description}",
		BarColumn(bar_width=None, style="black on black"),
		"[progress.percentage]{task.percentage:>3.0f}%",
		TimeRemainingColumn(),
		) as progress:

		task1 = progress.add_task("[red]Downloading...", total=1000)
		task2 = progress.add_task("[green]Processing...", total=1000)
		task3 = progress.add_task("[cyan]Cooking...", total=1000)

		while not progress.finished:
			progress.update(task1, advance=0.5)
			progress.update(task2, advance=0.3)
			progress.update(task3, advance=0.9)
			time.sleep(0.02)


if __name__ == '__main__':
	# main()
	progresstest()
