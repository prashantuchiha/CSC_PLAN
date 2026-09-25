import json
import logging
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
        )


def configure_logging(level: str, structured: bool) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        JSONFormatter() if structured else logging.Formatter("%(levelname)s %(name)s: %(message)s")
    )
    logging.basicConfig(level=level, handlers=[handler], force=True)
