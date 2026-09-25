class DomainError(Exception):
    """An expected business-rule or persistence boundary failure."""


class ValidationError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class ReferenceError(DomainError):
    pass
