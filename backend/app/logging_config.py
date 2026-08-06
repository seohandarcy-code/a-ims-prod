"""애플리케이션 공통 로깅 설정.

포맷: 시간 / 레벨 / 모듈명 / 메시지
레벨: INFO (기본값, 필요 시 LOG_LEVEL 환경변수로 오버라이드 가능)
"""
from __future__ import annotations

import logging
import os


def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
