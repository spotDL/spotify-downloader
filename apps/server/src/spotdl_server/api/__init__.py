"""HTTP API layer: routers, request/response schemas, and the error envelope.

This layer speaks FastAPI. It imports service classes and Pydantic API schemas —
never SQLAlchemy or ORM models (enforced in Task 12). Task 7 ships the stable
error envelope and exception handlers; routers and schemas arrive in Task 10.
"""
