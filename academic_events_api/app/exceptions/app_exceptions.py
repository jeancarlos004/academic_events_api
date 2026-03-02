from fastapi import HTTPException, status

class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class NotFoundException(AppException):
    def __init__(self, resource: str = "Recurso"):
        super().__init__(status.HTTP_404_NOT_FOUND, f"{resource} no encontrado")

class ConflictException(AppException):
    def __init__(self, detail: str = "Conflicto"):
        super().__init__(status.HTTP_409_CONFLICT, detail)

class ForbiddenException(AppException):
    def __init__(self, detail: str = "No tienes permisos"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail)

class UnauthorizedException(AppException):
    def __init__(self, detail: str = "No autenticado"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail)

class BadRequestException(AppException):
    def __init__(self, detail: str = "Solicitud inválida"):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)
