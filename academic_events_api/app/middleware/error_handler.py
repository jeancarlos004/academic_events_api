from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware:
    @staticmethod
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(
            "HTTPException: %s %s status=%s detail=%s",
            request.method,
            str(request.url),
            exc.status_code,
            exc.detail,
            exc_info=True,
        )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @staticmethod
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = [{"campo": " -> ".join(str(e) for e in err["loc"]), "mensaje": err["msg"]} for err in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": "Error de validación", "errores": errors})

    @staticmethod
    async def integrity_error_handler(request: Request, exc: SQLAlchemyError):
        logger.error(f"IntegrityError: {exc}")
        return JSONResponse(status_code=409, content={"detail": "Conflicto de datos"})

    @staticmethod
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled: {exc}", exc_info=True)
        
        # En desarrollo, mostrar el error completo
        error_detail = str(exc)
        
        return JSONResponse(
            status_code=500, 
            content={
                "detail": "Error interno del servidor",
                "error": error_detail,
                "type": type(exc).__name__
            }
        )
