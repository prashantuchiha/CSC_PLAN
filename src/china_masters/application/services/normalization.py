"""Conservative identifiers for research records."""

import re
from urllib.parse import urlsplit, urlunsplit

from china_masters.domain.exceptions import ValidationError


def normalized_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        raise ValidationError("Source URL must be an absolute HTTP(S) URL")
    host = parts.hostname.lower()
    try:
        port = parts.port
    except ValueError as exc:
        raise ValidationError("Invalid source URL port") from exc
    if parts.username or parts.password:
        raise ValidationError("Source URL credentials are not allowed")
    if ":" in host:
        host = f"[{host}]"
    default_port = (parts.scheme.lower() == "http" and port == 80) or (
        parts.scheme.lower() == "https" and port == 443
    )
    netloc = host if port is None or default_port else f"{host}:{port}"
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", parts.query, ""))


def normalized_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.casefold()).strip()


def normalized_doi(doi: str) -> str:
    return re.sub(
        r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", doi.strip(), flags=re.I
    ).casefold()
