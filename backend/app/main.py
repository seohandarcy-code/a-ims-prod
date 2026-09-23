import logging

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import access, admin, auth, dashboard, meta, status_detail
from app.config import CORS_ORIGINS, SESSION_COOKIE_SECURE, SESSION_SECRET_KEY
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

# SSO(AUTH_MODE=sso) 로그인 리다이렉트 중 OAuth state/nonce를 담아두는 용도.
# app/config.py의 SESSION_SECRET_KEY 참고 — AUTH_MODE=local이면 이 미들웨어는
# 그냥 아무것도 안 쓰인 채로 있는다. https_only는 SESSION_COOKIE_SECURE로 제어 —
# 실제 HTTPS 배포에서 true로 켠다.
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY, https_only=SESSION_COOKIE_SECURE)


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
app.include_router(access.router)
