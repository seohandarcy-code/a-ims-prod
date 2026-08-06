import logging

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, dashboard, meta, status_detail
from app.config import CORS_ORIGINS
from app.data.store import data_store
from app.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="IMS Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    logger.info("애플리케이션 시작")
    try:
        data_store.load()
    except Exception:
        logger.exception("시작 시 데이터 로드 실패")
        raise
    logger.info("애플리케이션 시작 완료")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready(response: Response) -> dict[str, str]:
    if not data_store.is_ready:
        response.status_code = 503
        return {"status": "not_ready"}
    return {"status": "ready"}


app.include_router(meta.router)
app.include_router(dashboard.router)
app.include_router(status_detail.router)
app.include_router(auth.router)
app.include_router(admin.router)
