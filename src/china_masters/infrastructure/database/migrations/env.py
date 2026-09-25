from typing import Any, Literal

from alembic import context

from china_masters.infrastructure.configuration.settings import Settings
from china_masters.infrastructure.database.engine import build_engine
from china_masters.infrastructure.database.models import Base
from china_masters.infrastructure.database.models.base import UTCDateTime


def render_item(kind: str, obj: Any, autogen_context: Any) -> str | Literal[False]:
    # Freeze the storage type in migration history; never import a mutable ORM model.
    if kind == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime()"
    return False


config = context.config
url = config.attributes.get("database_url") or Settings().database_url

if context.is_offline_mode():
    context.configure(
        url=url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = build_engine(url)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=Base.metadata,
                render_as_batch=True,
                compare_type=True,
                render_item=render_item,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
