"""Task 5 — whole-job progress mapping (CONTRACT 5) + the flush throttle."""

from __future__ import annotations

import pytest
from spotdl_core.download import ProgressPhase
from spotdl_server.downloads.progress import PHASE_WEIGHTS, ProgressThrottle, overall_progress


# ------------------------------------------------------------ overall_progress
def test_overall_progress_table() -> None:
    # fetch spans 0.05..0.60; at 50% -> 0.05 + 0.55*0.5 = 0.325
    assert overall_progress(ProgressPhase.FETCH, 50) == pytest.approx(0.325)
    # convert starts at 0.60
    assert overall_progress(ProgressPhase.CONVERT, 0) == pytest.approx(0.60)
    # done / skipped clamp to a full job
    assert overall_progress(ProgressPhase.DONE, None) == 1.0
    assert overall_progress(ProgressPhase.SKIPPED, None) == 1.0
    # error keeps 0.0 (weights (0,0))
    assert overall_progress(ProgressPhase.ERROR, None) == 0.0
    assert overall_progress(ProgressPhase.ERROR, 80) == 0.0
    # plan floor + a None percent maps to the phase floor
    assert overall_progress(ProgressPhase.PLAN, 0) == 0.0
    assert overall_progress(ProgressPhase.FETCH, None) == pytest.approx(0.05)


def test_overall_progress_clamps_to_unit_interval() -> None:
    # post spans 0.95..1.00; 200% overshoots -> clamp to 1.0
    assert overall_progress(ProgressPhase.POST, 200) == 1.0


def test_phase_weights_are_monotonic_non_overlapping() -> None:
    ordered = [
        ProgressPhase.PLAN,
        ProgressPhase.FETCH,
        ProgressPhase.CONVERT,
        ProgressPhase.EMBED,
        ProgressPhase.POST,
    ]
    for earlier, later in zip(ordered, ordered[1:], strict=False):
        assert PHASE_WEIGHTS[earlier][1] == pytest.approx(PHASE_WEIGHTS[later][0])


# ------------------------------------------------------------ ProgressThrottle
def test_throttle_terminal_always_flushes() -> None:
    throttle = ProgressThrottle(min_interval_ms=500)
    assert throttle.should_flush(now=0.0, phase=ProgressPhase.FETCH, overall=0.1, is_terminal=True)
    # a terminal frame flushes even with no time / delta advance
    assert throttle.should_flush(now=0.0, phase=ProgressPhase.FETCH, overall=0.1, is_terminal=True)


def test_throttle_phase_change_flushes() -> None:
    throttle = ProgressThrottle(min_interval_ms=500)
    # first frame: phase changed from None -> flush
    assert throttle.should_flush(now=0.0, phase=ProgressPhase.FETCH, overall=0.1, is_terminal=False)
    # same phase, no time/delta -> suppressed
    assert not throttle.should_flush(
        now=0.0, phase=ProgressPhase.FETCH, overall=0.105, is_terminal=False
    )
    # phase transition -> always flush (regardless of interval)
    assert throttle.should_flush(
        now=0.0, phase=ProgressPhase.CONVERT, overall=0.6, is_terminal=False
    )


def test_throttle_interval_and_delta_gate() -> None:
    throttle = ProgressThrottle(min_interval_ms=500)
    assert throttle.should_flush(now=0.0, phase=ProgressPhase.FETCH, overall=0.1, is_terminal=False)
    # enough delta but not enough time -> suppressed
    assert not throttle.should_flush(
        now=0.2, phase=ProgressPhase.FETCH, overall=0.3, is_terminal=False
    )
    # enough time but sub-delta -> suppressed
    assert not throttle.should_flush(
        now=0.6, phase=ProgressPhase.FETCH, overall=0.105, is_terminal=False
    )
    # enough time AND delta -> flush
    assert throttle.should_flush(now=0.6, phase=ProgressPhase.FETCH, overall=0.3, is_terminal=False)


def test_throttle_suppresses_rapid_subdelta_ticks() -> None:
    throttle = ProgressThrottle(min_interval_ms=500, min_delta=0.01)
    assert throttle.should_flush(
        now=0.0, phase=ProgressPhase.FETCH, overall=0.10, is_terminal=False
    )
    for tick in range(5):
        # plenty of wall-clock time each call, but progress barely moves
        assert not throttle.should_flush(
            now=1.0 + tick, phase=ProgressPhase.FETCH, overall=0.1005, is_terminal=False
        )
