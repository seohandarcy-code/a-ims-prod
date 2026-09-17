"""로컬 개발 DB를 .dat 백업으로 재구성하는 CLI.

운영에서 GET /api/v1/admin/export/dat (+ /export/column-types)로 내려받은 백업을
로컬 SQLite DB에 그대로 반영할 때 쓴다. 최초 시딩(app/db/seed.py.seed_if_empty)과
동일한 replace_all_from_dataframe()을 공유하므로 동작이 항상 일관된다.

사용 예:
    cd backend
    .venv\\Scripts\\python.exe scripts\\reseed_from_dat.py --file investment_backup.dat --reset
    .venv\\Scripts\\python.exe scripts\\reseed_from_dat.py --file investment_backup.dat --types column_types.json --reset
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.loader import read_dat  # noqa: E402
from app.db.seed import ensure_schema, replace_all_from_dataframe  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="dat 백업으로 로컬 DB 재시딩")
    parser.add_argument("--file", required=True, help="재시딩할 .dat 파일 경로")
    parser.add_argument("--types", help="커스텀 컬럼 타입 sidecar json 경로 (GET /export/column-types 응답, 선택)")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="기존 DB 내용을 모두 지우고 새로 채움 (지정하지 않으면 안전을 위해 실행하지 않는다)",
    )
    args = parser.parse_args()

    if not args.reset:
        print("경고: --reset 없이는 재시딩하지 않습니다 (기존 로컬 DB 내용을 실수로 지우지 않기 위한 안전장치).")
        raise SystemExit(1)

    ensure_schema()

    raw_df = read_dat(args.file)

    custom_types: dict[str, str] = {}
    if args.types:
        with open(args.types, "r", encoding="utf-8-sig") as f:
            custom_types = json.load(f)

    replace_all_from_dataframe(raw_df, custom_types)
    print(f"재시딩 완료: rows={len(raw_df)} source={args.file}")


if __name__ == "__main__":
    main()
