# 팀 투자 관리 시스템 (Vue + FastAPI + Nginx, No-DB, K8s/PDEP 배포)

이 프로젝트의 확정 개발 계획은 다음 문서를 참고한다: @docs/plan_v5.md

## 핵심 제약사항 (계획서 요약)
- 프론트엔드: Vue 3 + TypeScript, ECharts, 라이트/다크(프레젠테이션) 이중 테마
- 백엔드: FastAPI, **DB 미사용** — base 원본 파일, 또는 관리자가 편집하면 생성되는 `data_rev/*_rev.dat` 스냅샷(편집마다 전체 데이터를 덮어씀)을 그대로 로드. `edit_log.jsonl` append-only 감사이력 방식은 2026-07-24 세션에서 폐기(스냅샷 덮어쓰기로 단순화, 관련 코드는 `backend/app/data/edit_log.py`에 미사용 상태로 남아있음)
- 인증: 1단계는 관리자 단일 계정 로그인만 구현 (사이드바 하단 "관리자 설정" 진입점 → 팝업 내부 로그인/편집/비밀번호 변경). 비밀번호는 메모리에만 보관하며 서버 재기동 시 항상 기본값(`admin`/`0000`)으로 리셋됨(파일 영속화 안 함). AuthProvider는 local/sso 전환 가능하게 추상화
- 배포: Docker/K8s(PDEP), Nginx는 정적 서빙 + /api 내부 프록시만 담당 (TLS/외부 라우팅은 PDEP Ingress가 처리)
- 백엔드는 반드시 Replica=1로 운영 (파일 동시쓰기 문제 방지), PVC 필수
- 참고 레거시 코드: @legacy/web_new5_transfer_minus_detail.py (원본 COL/THEME 설계, 계산 로직 참고용)

## 기타 참고 사항 (클로드 코드 이전에 했던 참고 작업물)
- 참고 인풋 파일: @legacy/raw_new.dat
- 참고 환경 구성 폴더(github에 push): @../IMS_V1
- 참고 UI 이미지 폴더: @docs

## 작업 원칙
- 계획서(v5)와 다르게 구현해야 할 상황이 생기면 먼저 물어보고 진행할 것
- 코드 작성 전 항상 plan mode로 먼저 설계를 제시할 것
