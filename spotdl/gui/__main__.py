"""
Allow launching the GUI with ``python -m spotdl.gui``.
"""

import sys

from spotdl.gui import main

if __name__ == "__main__":
    sys.exit(main())
