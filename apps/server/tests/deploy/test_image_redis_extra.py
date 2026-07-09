"""Deferred image smoke: the hosted image must bundle the ``redis`` extra.

Plan 11 Task 5 bakes the ``redis`` extra into the published image
(``uv sync … --extra redis`` in ``deploy/Dockerfile``, CONTRACT B) so the
Redis-backed rate limiter activates purely on ``SPOTDL_REDIS_URL`` being set —
the same image self-hosters pull, with ``redis`` unused unless they opt in.

This test verifies that by running ``python -c "import redis"`` INSIDE the built
image. That requires the Dockerfile (Plan 11 Task 2) to exist and an image to be
built, so it is **deferred**: it skips unless ``SPOTDL_IMAGE_REF`` points at a
built image (set it in the ``compose-smoke``/release CI once the image lands, or
locally after ``docker build -f deploy/Dockerfile -t spotdl:test .``).

Run locally with:

    SPOTDL_IMAGE_REF=spotdl:test uv run pytest \
        apps/server/tests/deploy/test_image_redis_extra.py
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

IMAGE_REF = os.environ.get("SPOTDL_IMAGE_REF")


@pytest.mark.skipif(
    IMAGE_REF is None,
    reason=(
        "deferred: set SPOTDL_IMAGE_REF to a built image to verify the redis "
        "extra is bundled (needs deploy/Dockerfile from Plan 11 Task 2)"
    ),
)
def test_redis_importable_inside_built_image() -> None:
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("docker not available")
    result = subprocess.run(
        [docker, "run", "--rm", str(IMAGE_REF), "python", "-c", "import redis"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        "`import redis` failed inside the hosted image — the redis extra is not "
        f"bundled (see deploy/Dockerfile --extra redis).\nstderr:\n{result.stderr}"
    )
