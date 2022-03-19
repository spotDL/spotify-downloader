from spotdl.console import console_entry_point
from spotdl._version import __version__

if __name__ == "__main__":
    import cProfile, pstats

    with cProfile.Profile() as pr:
        console_entry_point()

    stats = pstats.Stats(pr)
    stats.sort_stats(pstats.SortKey.TIME)
    stats.dump_stats(filename="spotdl-unoptimized.profile")
