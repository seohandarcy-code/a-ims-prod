# 팀 투자 관리 시스템 (Vue + FastAPI + Nginx, SQLite→PostgreSQL, K8s/PDEP 배포)

이 프로젝트의 확정 개발 계획은 다음 문서를 참고한다: @docs/plan_v5.md

DB 전환 로드맵(SQLite → PostgreSQL → 환경변수/Secret 관리 → SSO/사용자 권한 DB)은
@docs/db-migration-roadmap.md 를 참고한다. 환경변수/Secret 카탈로그는
@docs/ENV_AND_SECRETS.md 를 참고한다.

## 핵심 제약사항 (계획서 요약)
- 프론트엔드: Vue 3 + TypeScript, ECharts, 라이트/다크(프레젠테이션) 이중 테마
- 백엔드: FastAPI. 데이터 계층은 **SQLite(1단계, 2026-09-16부터 적용) → PostgreSQL(2단계, 예정)**
  — 원래 v4/v5 계획서가 확정했던 No-DB 파일 스냅샷 구조에서 전환했다(v4 §1.3(f)가
  옵션으로 남겨둔 경로를 실제로 착수). `backend/data/base/*.dat`(및 기존 파일 기반
  클론의 `data_rev/*_rev.dat`)는 DB가 비어있을 때 **최초 1회 시딩 소스**로만 쓰이고,
  이후로는 DB만 읽고 쓴다(`backend/app/db/seed.py`). 운영 DB 백업 ↔ 로컬 개발 재시딩은
  `GET /api/v1/admin/export/dat` + `backend/scripts/reseed_from_dat.py`로 처리한다.
  상세는 @docs/db-migration-roadmap.md . 과거 `edit_log.jsonl` append-only 감사이력
  방식은 2026-07-24 세션에서 이미 폐기되었고(스냅샷 덮어쓰기로 단순화), 그 전제를
  그대로 이어받아 DB에서도 "현재 상태" 스냅샷만 관리한다(단일 슬롯 되돌리기).
- 인증: 1단계는 관리자 단일 계정 로그인만 구현 (사이드바 하단 "관리자 설정" 진입점 → 팝업 내부 로그인/편집/비밀번호 변경). 비밀번호는 메모리에만 보관하며 서버 재기동 시 항상 기본값(`admin`/`0000`)으로 리셋됨(파일 영속화 안 함). AuthProvider는 local/sso 전환 가능하게 추상화
- 배포: Docker/K8s(PDEP), Nginx는 정적 서빙 + /api 내부 프록시만 담당 (TLS/외부 라우팅은 PDEP Ingress가 처리)
- 백엔드는 반드시 Replica=1로 운영 (SQLite 파일 동시쓰기 문제 방지 — PostgreSQL 전환 후 재검토 대상), PVC 필수(SQLite DB 파일 포함)
- 참고 레거시 코드: @legacy/web_new5_transfer_minus_detail.py (원본 COL/THEME 설계, 계산 로직 참고용)

## 기타 참고 사항 (클로드 코드 이전에 했던 참고 작업물)
- 참고 인풋 파일: @legacy/raw_new.dat
- 참고 환경 구성 폴더(github에 push): @../IMS_V1
- 참고 UI 이미지 폴더: @docs

## 작업 원칙
- 계획서(v5)와 다르게 구현해야 할 상황이 생기면 먼저 물어보고 진행할 것
- 코드 작성 전 항상 plan mode로 먼저 설계를 제시할 것
