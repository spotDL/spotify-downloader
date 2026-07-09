"""``spotdl search`` — ranked table over the resolution transport.

Injects a fake :class:`SpotdlClient` through the ``_support.open_client`` seam so
the command's rendering/limit wiring is exercised without a live transport.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager

import pytest
from spotdl_cli.__main__ import app
from spotdl_cli.commands import _support
from spotdl_cli.views import AlbumRefView, TrackView
from typer.testing import CliRunner

runner = CliRunner()


class FakeReadClient:
    """Records the search args and returns canned ``TrackView`` results."""

    def __init__(self, results: list[TrackView]) -> None:
        self._results = results
        self.search_calls: list[tuple[str, int]] = []

    async def search(self, q: str, *, limit: int = 10) -> list[TrackView]:
        self.search_calls.append((q, limit))
        return self._results[:limit]


@pytest.fixture
def install_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Callable[[object], None]]:
    """Yield a function that swaps ``open_client`` for one yielding ``client``."""

    def install(client: object) -> None:
        @asynccontextmanager
        async def _open(**_: object) -> AsyncIterator[object]:
            yield client

        monkeypatch.setattr(_support, "open_client", _open)

    yield install


def test_search_renders_table(install_client: Callable[[object], None]) -> None:
    track = TrackView(
        id="11111111-1111-1111-1111-111111111111",
        name="One More Time",
        artists=["Daft Punk"],
        duration_ms=224_000,
        album=AlbumRefView(id="al:1", name="Discovery"),
    )
    install_client(FakeReadClient([track]))

    result = runner.invoke(app, ["search", "one more time"])

    assert result.exit_code == 0
    assert "Daft Punk — One More Time" in result.output
    assert "Discovery" in result.output
    assert "3:44" in result.output


def test_search_limit_is_forwarded(install_client: Callable[[object], None]) -> None:
    tracks = [
        TrackView(
            id=f"00000000-0000-0000-0000-00000000000{i}",
            name=f"t{i}",
            artists=["a"],
            duration_ms=1000,
        )
        for i in range(5)
    ]
    client = FakeReadClient(tracks)
    install_client(client)

    result = runner.invoke(app, ["search", "q", "--limit", "2"])

    assert result.exit_code == 0
    assert client.search_calls == [("q", 2)]


def test_search_no_results(install_client: Callable[[object], None]) -> None:
    install_client(FakeReadClient([]))

    result = runner.invoke(app, ["search", "nothing"])

    assert result.exit_code == 0
    assert "no results" in result.output
