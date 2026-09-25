import re
import unicodedata
from pathlib import Path, PureWindowsPath
from uuid import UUID

from china_masters.domain.exceptions import ValidationError


def slug(name: str, entity_id: UUID) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    safe = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")[:48].rstrip("-")
    return f"{safe or 'entity'}-{entity_id.hex}"


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _resolve(self, relative_path: str) -> Path:
        windows = PureWindowsPath(relative_path)
        if windows.is_absolute() or windows.drive or ":" in relative_path:
            raise ValidationError("Storage paths must be relative")
        normalized = relative_path.replace("\\", "/")
        if ".." in normalized.split("/") or Path(normalized).is_absolute():
            raise ValidationError("Storage path traversal is forbidden")
        target = (self.root / normalized).resolve()
        if not target.is_relative_to(self.root) or target == self.root:
            raise ValidationError("Storage path must remain inside the workspace")
        return target

    def create_university_workspace(self, university_id: UUID, name: str) -> str:
        relative = f"universities/{slug(name, university_id)}"
        for child in ("university", "admission", "sources", "professors"):
            self._resolve(f"{relative}/{child}").mkdir(parents=True, exist_ok=True)
        return relative

    def create_professor_workspace(
        self, university_id: UUID, university_name: str, professor_id: UUID, professor_name: str
    ) -> str:
        university = self.create_university_workspace(university_id, university_name)
        relative = f"{university}/professors/{slug(professor_name, professor_id)}"
        for child in ("sources", "research", "study_plans", "emails"):
            self._resolve(f"{relative}/{child}").mkdir(parents=True, exist_ok=True)
        return relative

    def write_bytes(self, relative_path: str, content: bytes) -> str:
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path.relative_to(self.root).as_posix()

    def read_bytes(self, relative_path: str) -> bytes:
        return self._resolve(relative_path).read_bytes()
