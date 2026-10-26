class DomainError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code, self.message, self.status_code = code, message, status_code
        super().__init__(message)

class NotFoundError(DomainError):
    def __init__(self, message="Resource not found"):
        super().__init__("NOT_FOUND", message, 404)

class ForbiddenError(DomainError):
    def __init__(self, message="Forbidden"):
        super().__init__("FORBIDDEN", message, 403)
