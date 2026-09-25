from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from china_masters.bootstrap import Container
from china_masters.infrastructure.configuration.settings import Settings
from china_masters.interfaces.api.app import create_app

ROOT = Path(__file__).resolve().parents[1]


def migrate(url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.attributes["database_url"] = url
    command.upgrade(config, "head")
    return config


@pytest.fixture
def settings(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        workspace_root=tmp_path / "workspace",
        _env_file=None,
    )
    migrate(settings.database_url)
    return settings


@pytest.fixture
def container(settings):
    container = Container(settings)
    yield container
    container.close()


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client
