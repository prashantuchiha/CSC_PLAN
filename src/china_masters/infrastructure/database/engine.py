from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url


def build_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    options: dict[str, Any] = {"pool_pre_ping": True}
    if url.get_backend_name() == "sqlite":
        if url.database and url.database != ":memory:":
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        options["connect_args"] = {"check_same_thread": False, "timeout": 10}
    engine = create_engine(url, **options)
    if url.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def sqlite_connect(connection: Any, record: Any) -> None:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=10000")
            cursor.close()

    return engine
