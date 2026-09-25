from uuid import UUID

from china_masters.application.ports.integrations import FileStorage
from china_masters.application.services.professors import ProfessorService
from china_masters.application.services.universities import UniversityService
from china_masters.domain.exceptions import ValidationError


class WorkspaceService:
    def __init__(
        self, storage: FileStorage, universities: UniversityService, professors: ProfessorService
    ) -> None:
        self._storage = storage
        self._universities = universities
        self._professors = professors

    def for_university(self, university_id: UUID) -> str:
        university = self._universities.get(university_id)
        return self._storage.create_university_workspace(university.id, university.canonical_name)

    def for_professor(self, professor_id: UUID) -> str:
        professor = self._professors.get(professor_id)
        university = self._universities.get(professor.university_id)
        return self._storage.create_professor_workspace(
            university.id, university.canonical_name, professor.id, professor.name_en
        )

    def save_professor_research_notes(
        self, professor_id: UUID, content: str, *, kind: str = "notes"
    ) -> str:
        if kind not in {"notes", "summary"}:
            raise ValidationError("Research note kind must be notes or summary")
        if len(content.encode("utf-8")) > 100_000:
            raise ValidationError("Research note exceeds 100 KB")
        workspace = self.for_professor(professor_id)
        return self._storage.write_bytes(f"{workspace}/research/{kind}.md", content.encode("utf-8"))
