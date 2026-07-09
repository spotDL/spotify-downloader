"""``spotdl`` command implementations, each registered onto the Typer app.

Every command module exposes a ``register(app)`` function that the CLI entry
point calls, so command wiring stays additive and the entry point never grows a
giant import list. Commands drive the :class:`~spotdl_cli.client.SpotdlClient`
façade only — never the generated client or ``spotdl_core`` directly.
"""
