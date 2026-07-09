"""Pure, framework-free view-models over the Plan 8 ``SpotdlClient`` façade.

The Textual TUI (``spotdl_cli.tui``) is a thin presentation layer; **all** fetching,
reducing, formatting, validation, and feature-gating lives here and is unit-tested
against a fake client. These modules import only the stdlib, ``spotdl_cli.views``,
``spotdl_cli.errors``, and ``spotdl_cli.config`` — never ``textual``, the generated
client, ``httpx``, or ``spotdl_server`` (CONTRACT I; enforced by import-linter's
``viewmodels_framework_free`` contract plus an AST guard).
"""
