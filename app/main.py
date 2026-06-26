import logging
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import router
from app.core.errors import AppError, app_error_handler
from app.db import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("project-activity-api")

app = FastAPI(title="Project Activity API", version="1.0.0")


@app.middleware("http")
async def request_logging(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info("request_complete method=%s path=%s status=%s elapsed_ms=%s", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


app.add_exception_handler(AppError, app_error_handler)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("unhandled_error path=%s", request.url.path)
    return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": "Unexpected server error"}})


@app.get("/health/live")
async def live():
    return {"status": "live"}


@app.get("/health/ready")
async def ready():
    async with SessionLocal() as session:
        await session.execute(text("select 1"))
    return {"status": "ready"}


app.include_router(router, prefix="/api/v1")
