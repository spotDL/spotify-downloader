

# from spotdl.cli.display import NewProgressBar, stop
# import spotdl.cli.displayManager as displayManager
# import spotdl.cli.arguementHandler as arguementHandler
from rich.progress import Progress, BarColumn, TimeRemainingColumn
# from rich.progress import track
import time
# from rich import print

# from alive_progress import showtime, alive_bar

from rich.console import (
    Console,
    # ConsoleRenderable,
    # JustifyMethod,
    # RenderableType,
    # RenderGroup,
    # RenderHook,
)


import io
import sys
import signal
# import sys

import atexit
from sys import argv as cliArgs


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
	# print("[italic red]Hello[/italic red] World!", locals())
	# console = Console(force_terminal=True)
	with Progress(
		"[progress.description]{task.description}",
		BarColumn(bar_width=None, style="black on black"),
		"[progress.percentage]{task.percentage:>3.0f}%",
		TimeRemainingColumn(),
		transient=True,
		# console=console,
		# redirect_stdout=True,
		# redirect_stderr=True,
		# auto_refresh=False
		) as progress:

		task1 = progress.add_task("[red]Downloading...", total=100)
		task2 = progress.add_task("[green]Processing...", total=100)
		task3 = progress.add_task("[cyan]Cooking...", total=100, start=False)

		while not progress.finished:
			progress.update(task1, advance=0.5)
			progress.update(task2, advance=0.3)
			# progress.update(task3, advance=0.9)
			# progress.refresh()
			time.sleep(0.02)

def progresstest2():
	for step in track(range(100), style="black on black"):
		# do_step(step)
		time.sleep(0.01)

def progresstest3():
	bar = alive_bar(20, title='Title here', length=20)
	for i in range(20):
		bar(i)
		time.sleep(0.01)

def progresstest4():
	progressTheme = Progress(
		"[progress.description]{task.description}",
		BarColumn(bar_width=None, style="black on black"),
		"[progress.percentage]{task.percentage:>3.0f}%",
		TimeRemainingColumn()
		)


	progressTheme.__enter__() # Alternate of using with # or .start()?
	# bar2.__enter__

	task1 = progressTheme.add_task("[red]Downloading...", total=100)
	task2 = progressTheme.add_task("[green]Processing...", total=100)
	# task3 = progressTheme.add_task("[green]Processing...", total=100, start=False)



	while not progressTheme.finished:
		progressTheme.update(task1, advance=0.5)
		progressTheme.update(task2, advance=0.3)
		# progress.update(task3, advance=0.9)
		progressTheme.refresh()
		time.sleep(0.002)
	progressTheme.stop() # CRUCIAL if funning outside with object

def progresstest5():
    # signal.signal(signal.SIGINT, signal_handler)
    # print('Press Ctrl+C')
    # signal.pause()
    v1 = displayManager.NewProgressBar("1")
    time.sleep(1)
    v1.setProgress(50)
    displayManager.log('stuff')
    time.sleep(1)
    # v1.setProgress(100)
    v1.done()
    time.sleep(1)
    # v1.close()
    displayManager.stop()


with Progress(
    "[progress.description]{task.description}",
    BarColumn(bar_width=None, style="black on black"),
    "[progress.percentage]{task.percentage:>3.0f}%",
    TimeRemainingColumn(),
) as progress:
    def progresstest6():
        print('assdf')

        task1 = progress.add_task("[red]Downloading...", total=100)
        task2 = progress.add_task("[green]Processing...", total=100)
        task3 = progress.add_task("[cyan]Cooking...", total=100, start=False)

        while not progress.finished:
            progress.update(task1, advance=0.5)
            progress.update(task2, advance=0.3)
            # progress.update(task3, advance=0.9)
            # progress.refresh()
            time.sleep(0.02)



# def signal_handler(sig, frame):
#     print('You pressed Ctrl+C!')
#     displayManager.stop()
#     sys.exit(0)

# def exit_handler(quit=False):
#     # print('I exited i guess')
#     displayManager.stop()
#     if quit:
#         sys.exit(0)

# def argtest1():
#     arguementHandler.passArgs(cliArgs)


# atexit.register(exit_handler)
# signal.signal(signal.SIGTERM, signal_handler)
# signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':
	# main()
	# progresstest()
	# progresstest2()
	# progresstest3()
	# progresstest4()
    try:
        
        # progresstest5()
        progresstest6()
        # argtest1()
        # print(f)
    except Exception as inst:
        # displayManager.log("there was an unknown error of:   " + str(inst.__str__()))
        # displayManager.log(str(inst.args))
        # exit_handler()
        raise
	# showtime()
	# alive_test()

# exit_handler()