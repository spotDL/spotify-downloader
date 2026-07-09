# API reference

The spotDL server exposes a versioned HTTP API under `/api/v1`. The reference
below is rendered from the server's OpenAPI schema (`apps/server/openapi.json`),
which describes the **full** surface (the self-host build, including the
downloads/queue endpoints).

- **Community API base URL:** `https://api.spotdl.dev`
- **Self-hosted:** the same API is served from your instance's root.

<swagger-ui src="openapi.json"/>

!!! note
    The schema is a committed build artifact kept in sync by the server's tests.
    It is copied into this page at docs-build time from
    `apps/server/openapi.json`; it is not maintained separately.
