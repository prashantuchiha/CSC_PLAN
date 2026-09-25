"""Add a conservative source URL identity key.

Revision ID: c924ad29e762
Revises: ee8576e1a3fb
"""

from urllib.parse import urlsplit, urlunsplit

import sqlalchemy as sa
from alembic import op

revision = "c924ad29e762"
down_revision = "ee8576e1a3fb"
branch_labels = None
depends_on = None


def _key(url: str) -> str | None:
    try:
        parts = urlsplit(url.strip())
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            return None
        host = parts.hostname.lower()
        if ":" in host:
            host = f"[{host}]"
        port = parts.port
        default = (parts.scheme.lower(), port) in {("http", 80), ("https", 443)}
        netloc = host if port is None or default else f"{host}:{port}"
        return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", parts.query, ""))
    except ValueError:
        return None


def upgrade() -> None:
    with op.batch_alter_table("sources") as batch:
        batch.add_column(sa.Column("normalized_url", sa.Text(), nullable=True))
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, url FROM sources ORDER BY id"))
    seen: set[str] = set()
    for source_id, url in rows:
        key = _key(url)
        if key is None or key in seen:
            # Keep historical duplicates and all their foreign keys intact.
            continue
        seen.add(key)
        conn.execute(
            sa.text("UPDATE sources SET normalized_url = :key WHERE id = :source_id"),
            {"key": key, "source_id": source_id},
        )
    with op.batch_alter_table("sources") as batch:
        batch.create_index("ix_sources_normalized_url", ["normalized_url"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("sources") as batch:
        batch.drop_index("ix_sources_normalized_url")
        batch.drop_column("normalized_url")
