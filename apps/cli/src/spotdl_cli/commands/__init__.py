"""``spotdl`` command modules.

Each module owns one command (or command group) and exposes a ``register(app)``
hook that :mod:`spotdl_cli.__main__` calls to attach it to the root Typer app.
Keeping registration additive (one ``register`` call per module) is what lets the
parallel Plan 8 command tracks land without fighting over ``__main__``.
"""
