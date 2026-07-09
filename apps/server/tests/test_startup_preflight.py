import pytest
from spotdl_server.app import create_app
from spotdl_server.settings import DeploymentMode, Settings


async def test_unmigrated_db_raises_clear_error(tmp_path):
    """A fresh (unmigrated) data dir must fail with an actionable message, not
    a raw 'no such table' deep in orphan recovery."""
    settings = Settings(mode=DeploymentMode.EMBEDDED, data_dir=tmp_path)
    app = create_app(settings)
    with pytest.raises(RuntimeError, match="not migrated"):
        async with app.router.lifespan_context(app):
            pass
