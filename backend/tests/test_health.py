"""헬스체크 엔드포인트 최소 테스트.

/health, /health/live, /health/ready 세 엔드포인트의 기본 동작을 확인한다.
TestClient를 컨텍스트 매니저로 사용해 FastAPI startup 이벤트
(data_store.load())가 실행되도록 한다.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_live_ok():
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_health_ready_after_startup():
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
