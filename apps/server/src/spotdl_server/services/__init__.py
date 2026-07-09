"""Service layer: orchestration between the API and the repositories/core.

Services import repositories and ``spotdl_core`` — never FastAPI — and keep no
FastAPI or SQLAlchemy types in their public signatures (enforced in Task 12).
Task 7 ships the server-side ``NotFoundError``; the resolve/search/entity
services arrive in Tasks 8/9.
"""
