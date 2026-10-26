import asyncio

from datastar_py.fastapi import ServerSentEventGenerator as SSE
from fastapi import FastAPI

from spotdl.web import routes
from spotdl.web.utils import datastar_response


async def call_asgi(app, path, query_string=b""):
    """Make a GET request to an ASGI app, return the status, headers and body"""

    messages = []
    request_sent = False

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}

        # Keep the connection open until the response is done
        await asyncio.sleep(3600)

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string,
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8800),
    }

    await asyncio.wait_for(app(scope, receive, send), timeout=10)

    start = next(m for m in messages if m["type"] == "http.response.start")
    body = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )

    return start["status"], dict(start["headers"]), body


async def test_datastar_response_streams_events():
    app = FastAPI()

    @app.get("/greet")
    @datastar_response
    async def greet(name: str):
        yield SSE.patch_elements(f'<div id="greeting">Hello {name}</div>')

    status, headers, body = await call_asgi(app, "/greet", b"name=spotdl")

    assert status == 200
    assert headers[b"content-type"].startswith(b"text/event-stream")
    assert b"Hello spotdl" in body


def test_routes_use_datastar_response_without_wrapped():
    for route in routes.router.routes:
        assert not hasattr(route.endpoint, "__wrapped__"), route.path
