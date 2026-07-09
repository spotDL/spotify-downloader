from importlib.metadata import version

import spotdl_core


def test_version_matches_distribution_metadata() -> None:
    # Bump-stable single-source check: the in-package ``__version__`` must equal the
    # version installed from pyproject. ``scripts/bump_version.py`` writes both in
    # lockstep and CI's ``version-consistency`` step guards the whole workspace; this
    # asserts the two never drift for ``spotdl-core`` regardless of the current number.
    assert spotdl_core.__version__ == version("spotdl-core")
