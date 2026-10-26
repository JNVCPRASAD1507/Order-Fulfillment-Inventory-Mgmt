from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.errors import DomainError
from app.api.routes import router


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Production-oriented order fulfillment and inventory API",
)

app.include_router(router, prefix="/api")


@app.exception_handler(DomainError)
async def domain_handler(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc.errors()),
            },
        },
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
    }