from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routes.jargon import router as jargon_router
from app.routes.chat import router as chat_router

app = FastAPI(
    title="SIH 26 AI-ML Stuff",
    description="Stateless AI/ML microservice for scheme matching, document processing, and vernacular advisory.",
    version="1.0.0",
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code = "BAD_REQUEST"
    if exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code >= 500:
        code = "INTERNAL_SERVER_ERROR"

    message = str(exc.detail)
    details = None

    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", code)
        message = exc.detail.get("message", exc.detail.get("detail", message))
        details = exc.detail.get("details", None)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    details = []
    for err in errors:
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "")
        details.append(f"{loc}: {msg}")

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Schema validation failed or request payload is invalid.",
                "details": "; ".join(details) if details else None,
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing the request.",
                "details": str(exc),
            }
        },
    )


app.include_router(jargon_router)
app.include_router(chat_router)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Lmao Hi",
        "docs_url": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
