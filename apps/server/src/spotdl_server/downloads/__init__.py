"""Leaf download-domain package (pure-ish; no FastAPI, no ORM) below services.

Holds the ``.spotdl`` v2 save-file model (Task 2), whole-job progress mapping
(Task 5), and the worker pool + crash-recovery state machine (Task 6). Everything
here speaks plain Python + Pydantic value types and the Plan 4 download engine —
never HTTP or SQLAlchemy types in its public surface.
"""
