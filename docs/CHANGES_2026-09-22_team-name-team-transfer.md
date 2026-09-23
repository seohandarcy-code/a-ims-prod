# 2026-09-22 변경사항: 팀명 변경 + 계획구분 "타팀이관" 추가

## 이 문서의 목적

이 저장소를 다른 컴퓨터에서도 이어서 작업 중일 때, 이 컴퓨터에서 2026-09-22에 커밋한 변경사항을
그쪽 작업 폴더에도 동일하게 반영하기 위한 안내서입니다. **코드뿐 아니라 데이터 파일 값도 함께
바뀌었으므로, 코드만 반영하고 데이터를 맞추지 않으면 화면이 어긋납니다.**

- 관련 커밋: `de062f3` — `feat: 팀명 변경(인프라AX/PI팀) 및 계획구분 "타팀이관" 추가`
- 이 커밋이 올라가 있는 브랜치: `ui_design_rev_0811`, `0922_dev` (origin에 모두 push됨)

## 0. 가장 쉬운 적용 방법 — git으로 동기화

다른 컴퓨터의 폴더도 같은 GitHub 저장소(`origin`)를 보고 있다면, 아래 diff를 손으로 옮기지 않고
그냥 git으로 받아오는 게 가장 안전합니다.

```powershell
git fetch origin
git checkout ui_design_rev_0811   # 또는 git checkout 0922_dev
git merge origin/ui_design_rev_0811
```

로컬에 아직 커밋하지 않은 다른 작업이 있다면 먼저 `git stash`로 보관한 뒤 위 명령을 실행하고,
끝나면 `git stash pop`으로 되돌리세요. **아래 1~2번 섹션은 git 동기화가 불가능한 상황(예: 별도로
분기된 사본이라 git 이력이 다름)에서 수동으로 반영할 때만 참고하면 됩니다.**

## 배경 (왜 바꿨는지)

1. **팀명 변경**: 실제 팀명이 "A-Infra기술팀" → "인프라AX/PI팀"으로 바뀌었습니다. 화면에 보이는
   문자열은 먼저 바뀌었지만, "조직 구분"의 "전체" 필터가 내부적으로 이 팀명 문자열과 **글자 단위로
   정확히 일치**해야 동작하는 sentinel 값(`PJT_TOTAL_LABEL`)이라, 이름이 반쪽만 바뀌면서 "전체"
   필터가 정상 동작하지 않는 문제가 있었습니다. 이번에 코드 상수·데이터 값을 모두 새 이름으로
   맞춰서 해결했습니다.
2. **계획구분 "타팀이관" 추가**: 계획구분(투자 진행 흐름 구분)에 "타팀이관"(다른 팀으로 이관되어
   더 이상 우리 팀 투자가 아닌 건)이 새로 필요해져, 기존 "Drop"과 동일한 성격(전체 투자계획에는
   포함하되 진행 투자계획에는 제외)으로 추가했습니다.
3. **표시 순서/문구 조정**: 오너 피드백으로 화면상 Drop/타팀이관 표시 순서를 교체(타팀이관을
   먼저)하고, "전체 투자계획" KPI 카드의 설명 문구도 그 순서에 맞게 수정했습니다.

## 1. 데이터 변경 (`backend/data/base/raw_dt_new2_rev.dat`)

이 파일은 서버가 실제로 로드하는 원본 데이터입니다(`backend/app/config.py`의 `BASE_FILE`).

| 대상 | 컬럼 | 이전 값 | 새 값 |
|---|---|---|---|
| 전체 34행 | `팀` | `A-Infra기술팀` | `인프라AX/PI팀` |
| NO 22 | `계획구분` | `Drop` | `타팀이관` |
| NO 33 | `계획구분` | `Drop` | `타팀이관` |

> NO 9는 계속 `Drop`으로 남겨뒀습니다(화면에 Drop/타팀이관 두 값이 동시에 보이도록 검증용으로
> 남긴 것). 최종 계획구분 분포: 계획 26 / 계획외 5 / Drop 1 / 타팀이관 2 (총 34건).

다른 컴퓨터의 데이터 파일이 이 저장소와 동일한 `raw_dt_new2_rev.dat`를 쓰고 있다면, 위 표대로
텍스트 치환(정확히 이 3곳만)하면 됩니다. 파일은 탭 구분(TSV), UTF-8입니다.

## 2. 코드 변경 파일별 요약

### `backend/app/data/columns.py`
```diff
-PJT_TOTAL_LABEL = "A-Infra기술팀"
+PJT_TOTAL_LABEL = "인프라AX/PI팀"
```
"조직 구분"의 "전체" sentinel. 위 데이터 변경(팀 컬럼 값)과 반드시 글자 단위로 일치해야 합니다.

### `backend/app/api/meta.py`
```diff
-        team_name="A-Infra기술팀",
+        team_name="인프라AX/PI팀",
```
헤더 타이틀/"선택된 조직: 전체" 라벨용 문자열(`PJT_TOTAL_LABEL`과는 별도로 관리되는 하드코딩값).

### `frontend/src/App.vue`
```diff
-        {{ meta?.team_name ?? 'A-Infra기술팀' }}
+        {{ meta?.team_name ?? '인프라AX/PI팀' }}
```
`meta` API 응답이 오기 전 잠깐 보이는 fallback 문자열(동작에는 영향 없는 코스메틱 변경).

### `backend/app/calc/stage.py` — 계획구분 "타팀이관"을 Drop과 같은 방식으로 추가
- `FUNNEL_MASK_KEYS` 튜플에 `"team_transfer"` 추가.
- `_funnel_masks()`에 `team_transfer_mask = plan_type == "타팀이관"` 추가, 반환 dict에도 추가.
- `FUNNEL_ITEMS`(퍼널 차트/사이드바 필터가 공유하는 단일 소스 리스트)에
  `("team_transfer", "타팀이관", "component", "plan")` 항목을 `plan_out` 다음, `drop` 앞에 추가
  — 이 위치가 화면상 "타팀이관 먼저, Drop 나중" 순서를 결정합니다.
- `make_progress_funnel()`의 "전체 투자계획" 카운트 계산식에 `team_transfer` 마스크를 OR로 추가:
  `masks["plan"] | masks["plan_out"] | masks["drop"] | masks["team_transfer"]`.

`funnel_filter_options()`(사이드바 "투자 진행 흐름 구분" 필터 옵션)와 `make_progress_funnel()`
둘 다 `FUNNEL_ITEMS`를 그대로 파생시키는 구조라, 이 리스트 수정 한 곳으로 퍼널 차트/사이드바
필터/필터 클릭 동작(`funnel_key_mask`/`flow_stage_mask`)이 전부 자동으로 반영됩니다.

### `backend/app/api/dashboard.py`
```diff
-    plan_total_df = detail_filtered_df[detail_filtered_df[COL["plan_type"]].isin(["계획", "계획외", "Drop"])]
+    plan_total_df = detail_filtered_df[
+        detail_filtered_df[COL["plan_type"]].isin(["계획", "계획외", "Drop", "타팀이관"])
+    ]
```
"전체 투자계획" KPI 카드 스코프. "진행 투자계획"(`plan_progress_df`, `.isin(["계획","계획외"])`)은
그대로 둬서 Drop과 마찬가지로 타팀이관도 계속 제외됩니다.

### `frontend/src/components/charts/StageExpandedWaterfallChart.vue`
- 기존에 Drop만을 위해 하드코딩했던 `dropCount`/`.drop-chip` 엘리먼트 1개를, `HIDDEN_BAR_KEYS`에
  포함된 항목(현재 `drop`, `team_transfer`)을 모두 그려주는 `sideChips` computed +
  `v-for="chip in sideChips"`로 일반화했습니다. `HIDDEN_BAR_KEYS`에 `'team_transfer'`를 추가.
- CSS 클래스명 `.drop-chip` → `.side-chip`으로 일반화(스타일 자체는 동일하게 재사용 — 배경색
  `--trailing-gray`, 폭/폰트/hover/active 등 변경 없음).
- `sideChips`는 `FUNNEL_ITEMS` 순서를 그대로 따르므로, `FUNNEL_ITEMS`에서 `team_transfer`가
  `drop`보다 앞에 있으면 화면에도 "타팀이관 칩 위, Drop 칩 아래" 순서로 나타납니다.

### `frontend/src/components/table/DetailTable.vue`
```diff
-            :class="{ 'row-dropped': row.plan_type === 'Drop' }"
+            :class="{ 'row-dropped': isDroppedRow(row) }"
```
`DROPPED_PLAN_TYPES = new Set(['Drop', '타팀이관'])`를 추가해, 상세리스트에서 타팀이관 행도
Drop과 동일하게 회색으로 표시됩니다.

### `frontend/src/views/DashboardView.vue`
```diff
-      caption: '계획 + 계획외 + Drop',
+      caption: '계획 + 계획외 + 타팀이관 + Drop',
```
"전체 투자계획" KPI 카드 설명 문구(및 근처 주석)를 새 순서에 맞게 수정.

## 3. 반영 후 검증 체크리스트

- [ ] 백엔드 재시작 후 `GET /api/v1/meta` 응답의 `team_name`, `org_options[0]`이 `인프라AX/PI팀`인지 확인
- [ ] `GET /api/v1/dashboard`를 `selected_org` 없이 호출한 결과와 `selected_org=인프라AX/PI팀`로
      호출한 결과의 `detail_rows` 건수가 동일한지 확인("전체" 필터 정상 동작 확인)
- [ ] `GET /api/v1/meta`의 `flow_stage_options`, `GET /api/v1/dashboard`의 `progress_funnel`에서
      `team_transfer` 항목이 `drop`보다 앞에 오는지 확인
- [ ] `executive_kpi.total_count`(전체 투자계획)에 타팀이관 2건이 포함되고,
      `progress_count`(진행 투자계획)에는 제외되는지 확인
- [ ] 브라우저에서 퍼널 축 옆 칩이 "타팀이관 → Drop" 순서로, KPI 캡션이
      "계획 + 계획외 + 타팀이관 + Drop"으로 보이는지 확인
- [ ] 상세리스트에서 타팀이관 2건(NO 22, 33)이 Drop과 동일하게 회색으로 표시되는지 확인
- [ ] 사이드바 "투자 진행 흐름 구분" 필터 목록에 "타팀이관"이 "Drop"보다 먼저 나오는지 확인
