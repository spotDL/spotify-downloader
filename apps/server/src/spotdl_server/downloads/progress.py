"""Whole-job progress mapping (CONTRACT 5) + the per-job flush throttle.

The engine reports **per-phase** progress (``ProgressPhase`` + an optional 0-100
in-phase percent). Clients want a single monotonic 0.0-1.0 whole-job value, so
:func:`overall_progress` maps a phase + in-phase percent onto a fixed weight band
per :data:`PHASE_WEIGHTS`. The bands are contiguous and non-overlapping (each
phase's ``hi`` equals the next phase's ``lo``), so the mapped value never goes
backwards as the pipeline advances.

:class:`ProgressThrottle` is the pump's flush policy: it collapses the engine's
rapid in-phase ticks down to at most one persisted-row-write + WS broadcast per
``min_interval_ms``, while never dropping a phase transition or a terminal frame.
``PHASE_WEIGHTS`` / ``overall_progress`` are CONTRACT; the throttle internals are
free.
"""

from __future__ import annotations

from spotdl_core.download import ProgressPhase

# Each phase owns a contiguous ``(lo, hi)`` slice of the 0..1 whole-job bar.
# FETCH is the widest band (the dominant cost); DONE/SKIPPED pin to 1.0; ERROR
# leaves the bar where it was (both bounds 0.0 so the mapper never advances it).
PHASE_WEIGHTS: dict[ProgressPhase, tuple[float, float]] = {
    ProgressPhase.PLAN: (0.00, 0.05),
    ProgressPhase.FETCH: (0.05, 0.60),
    ProgressPhase.CONVERT: (0.60, 0.85),
    ProgressPhase.EMBED: (0.85, 0.95),
    ProgressPhase.POST: (0.95, 1.00),
    ProgressPhase.DONE: (1.00, 1.00),
    ProgressPhase.SKIPPED: (1.00, 1.00),
    ProgressPhase.ERROR: (0.00, 0.00),  # progress left as-is on error
}


def overall_progress(phase: ProgressPhase, percent: int | None) -> float:
    """Map a phase + in-phase percent to a monotonic 0.0-1.0 whole-job value.

    ``lo + (hi - lo) * (percent or 0) / 100``, clamped to ``[0, 1]``.
    ``DONE`` / ``SKIPPED`` always report a full job (1.0); ``ERROR`` reports 0.0
    (the pump keeps the row's last persisted value on error).
    """
    lo, hi = PHASE_WEIGHTS[phase]
    fraction = (percent or 0) / 100.0
    value = lo + (hi - lo) * fraction
    return max(0.0, min(1.0, value))


class ProgressThrottle:
    """Decide when a per-job progress frame is worth a row-write + WS broadcast.

    A frame flushes when it is *terminal*, when its *phase changed* since the last
    flush, or when both enough wall-clock time (``min_interval_ms``) has elapsed
    **and** the whole-job value advanced by at least ``min_delta``. Rapid in-phase
    sub-delta ticks are suppressed. The decision state is recorded only on a
    ``True`` return, so a suppressed tick never resets the interval/delta window.
    """

    def __init__(self, *, min_interval_ms: int, min_delta: float = 0.01) -> None:
        self._min_interval_s = min_interval_ms / 1000.0
        self._min_delta = min_delta
        self._last_time: float | None = None
        self._last_phase: ProgressPhase | None = None
        self._last_overall: float = 0.0

    def should_flush(
        self, *, now: float, phase: ProgressPhase, overall: float, is_terminal: bool
    ) -> bool:
        """Return whether this frame should be flushed (and record it if so)."""
        if is_terminal:
            self._record(now, phase, overall)
            return True
        if phase != self._last_phase:  # includes the first-ever frame (None -> phase)
            self._record(now, phase, overall)
            return True
        if self._last_time is not None and (
            now - self._last_time >= self._min_interval_s
            and overall - self._last_overall >= self._min_delta
        ):
            self._record(now, phase, overall)
            return True
        return False

    def _record(self, now: float, phase: ProgressPhase, overall: float) -> None:
        self._last_time = now
        self._last_phase = phase
        self._last_overall = overall
