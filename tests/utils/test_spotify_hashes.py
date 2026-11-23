from spotapi.client import BaseClient

from spotdl.utils import spotify


def test_web_player_hashes_are_downloaded_once(monkeypatch):
    calls = []

    def fake_get_sha256_hash(self):
        calls.append(self)
        self.raw_hashes = "hashes"

    monkeypatch.setattr(BaseClient, "get_sha256_hash", fake_get_sha256_hash)
    monkeypatch.setattr(spotify, "_SHARED_HASHES", {})

    spotify._share_web_player_hashes()
    first = BaseClient.__new__(BaseClient)
    second = BaseClient.__new__(BaseClient)
    first.get_sha256_hash()
    second.get_sha256_hash()

    assert len(calls) == 1
    assert second.raw_hashes == "hashes"


def test_web_player_hashes_expire(monkeypatch):
    calls = []

    def fake_get_sha256_hash(self):
        calls.append(self)
        self.raw_hashes = f"hashes-{len(calls)}"

    monkeypatch.setattr(BaseClient, "get_sha256_hash", fake_get_sha256_hash)
    monkeypatch.setattr(spotify, "_SHARED_HASHES", {})
    monkeypatch.setattr(spotify, "_HASHES_TTL", 0.0)

    spotify._share_web_player_hashes()
    first = BaseClient.__new__(BaseClient)
    second = BaseClient.__new__(BaseClient)
    first.get_sha256_hash()
    second.get_sha256_hash()

    assert len(calls) == 2
    assert second.raw_hashes == "hashes-2"
