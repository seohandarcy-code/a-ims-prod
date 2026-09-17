# raw_dt_new3.dat 데이터 변경 안내

2026-09-17, 팀명이 변경되어 `팀` 컬럼 값을 일괄 치환한 파일입니다. 그 외 컬럼 구조/값은
`raw_dt_new2_rev.dat`(39 컬럼, 34행)와 완전히 동일합니다.

- 원본: `raw_dt_new2_rev.dat`
- 변경 내용: `팀` 컬럼 값 `A-Infra기술팀` → `인프라AX/PI기술팀` (전 34행 동일 적용, 그 외 값 변경 없음)
- 형식: TSV(tab-separated), UTF-8(BOM), CRLF — `app/data/writer.py`의 `atomic_write_dat()`으로 생성(기존 파일들과 동일 파이프라인)

이전 파일(`raw_dt_new2_rev.dat` 이하)은 롤백용으로 그대로 보존합니다.
