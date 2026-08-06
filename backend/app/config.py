from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / os.getenv("DATA_DIR", "data")

BASE_DIR = DATA_DIR / "base"
EDITS_DIR = DATA_DIR / "edits"
CURRENT_DIR = DATA_DIR / "current"
DATA_REV_DIR = DATA_DIR / "data_rev"

# 2026-08-04: 팀/PJT/파트 3단계 조직 계층을 도입하며 raw_2026_07.dat(29컬럼, "조직" 단일
# 레벨)에서 raw_dt_new.dat(38컬럼, 팀/PJT/파트+9개 신규 컬럼)로 전환.
# 2026-08-05: 기성(집행) 데이터 정합성 수정 + 투자완료 컬럼이 추가된 raw_dt_new2.dat(39컬럼)로
# 재전환. 이전 파일들은 롤백용으로 base/ 아래 그대로 보존한다.
# 2026-08-06: 기준월(9월)보다 미래 시점이 "이미 실적"으로 잘못 기록된 3건(NO 12/18/31)을 바로잡은
# raw_dt_new2_rev.dat(컬럼 구조 동일, 39컬럼)로 교체. 상세 내역은 data/base/DATA_CHANGES2_rev.md 참고.
BASE_FILE = BASE_DIR / "raw_dt_new2_rev.dat"
EDIT_LOG_FILE = EDITS_DIR / "edit_log.jsonl"
CURRENT_FILE = CURRENT_DIR / "current_dataset.dat"
REV_FILE = DATA_REV_DIR / f"{BASE_FILE.stem}_rev.dat"
REV_BACKUP_FILE = DATA_REV_DIR / f"{BASE_FILE.stem}_rev.bak.dat"

# 커스텀 컬럼(관리자가 추가한 컬럼)의 타입을 기억하는 sidecar 메타 파일.
# raw_df 자체는 값만 담고 타입 정보가 없어 재기동 후에도 타입을 유지하려면 별도 저장이 필요하다.
CUSTOM_COLUMN_TYPES_FILE = DATA_REV_DIR / "custom_column_types.json"
CUSTOM_COLUMN_TYPES_BACKUP_FILE = DATA_REV_DIR / "custom_column_types.bak.json"

CURRENT_YEAR = int(os.getenv("CURRENT_YEAR", "2026"))

_month_override = os.getenv("CURRENT_MONTH_OVERRIDE", "").strip()
CURRENT_MONTH_OVERRIDE: int | None = int(_month_override) if _month_override else None

_default_cors_origins = "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8080"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", _default_cors_origins).split(",")
    if origin.strip()
]
