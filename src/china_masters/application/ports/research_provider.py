from typing import Protocol

from china_masters.application.ports.integrations import ResearchResult
from china_masters.domain.entities import Professor, University


class ResearchProvider(Protocol):
    """Narrow research subset of the future AI provider contract."""

    def research_professor(self, professor: Professor) -> ResearchResult: ...
    def research_university(self, university: University) -> ResearchResult: ...
