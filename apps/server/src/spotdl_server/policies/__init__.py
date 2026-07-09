"""Versioned, JSON-serializable policy configs for the community layer.

Modeled on the matcher's ``ScoringConfig``/``matcher_version``: thresholds live
in a frozen Pydantic model with a ``policy_version`` string so they are
recalibratable without code edits (spec §5 "versioned weights" philosophy). This
package sits below ``services`` and imports nothing from the server stack — a
pure leaf, importable by both ``services`` and ``api`` without a layering
violation.
"""
