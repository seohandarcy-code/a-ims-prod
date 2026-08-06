# 2026-07-20 디자인 업그레이드 리뷰 — 색상/타이포/비율/중복 정합성 점검

> 참여: `ui-designer`(디자이너 관점 의견) + `frontend-dev`(코드 기반 기술 조사), `pm-coordinator`(종합).
> 이 문서는 **검토/의견 수렴 결과만** 정리한 것이며, 이번 라운드에서 `.vue`/`.ts`/`.css` 등 실제 구현 파일은 어떤 것도 수정하지 않았다. 두 서브에이전트 모두 파일 수정 권한을 명시적으로 회수한 상태로 조사만 수행했다.
> 실제 실행 여부·우선순위·순서는 프로젝트 오너가 이 리뷰를 보고 별도로 지시한다.
>
> **전제(유지)**: 단계 색상 언어 — 품의=블루(`#1428A0`) / 계약=퍼플(`#7C3AED`) / 집행=그린(`#059669`)은 이미 구현되어 있고 이번에도 **코드 자체는 유지**한다. 이번 라운드는 색상 톤앤매너를 바꾸는 게 아니라, 그 위에서 발생한 **일관성/중복/위계** 문제를 다듬는 성숙화 패스다.
> 선행 리뷰(중복 방지용): `docs/design-review/2026-07-17-review.md`, `docs/design-review/2026-07-18-roundtable.md`.

---

## 0. 총평

선행 라운드에서 도입한 3단계 색상 언어(블루/퍼플/그린), `StageFunnelCard`, `InlineRatioBar`, KPI 상징색은 **실제로 구현이 반영됐다.** 이번 조사에서 두 에이전트가 독립적으로 도달한 공통 결론은 다음과 같다.

1. **색상**: 단계 hue(블루/퍼플/그린) 자체는 차트에 깨끗하게 적용됐으나, KPI **상태 톤 시스템(good/warn/bad)이 단계 색과 같은 채널(8px 좌측 바)·같은 색(good=품의 블루)** 을 써서 의미가 충돌한다. 같은 지표가 탭에 따라 hue가 바뀌는 곳도 있다.
2. **타이포**: 역할별 크기가 **토큰 없이 컴포넌트마다 하드코딩**되어, 같은 역할(제목/큰 숫자/표 본문/캡션)이 파일마다 다른 값으로 흩어져 있다. `small-title`과 `section-title`이 동일 1.4rem으로 위계가 붕괴.
3. **비율**: 차트 높이(340/340/320)와 표 높이(640/380/300 + 무제한 2개)가 **공유 상수 없이 리터럴로 산재**. 상세 탭의 좌(비율바 ~150px) vs 우(콤보차트 340px) 2열이 높이 불균형.
4. **중복**: 두 탭에 걸쳐 퍼널·진단표·전환율 KPI가 각각 2~4회 반복. 백엔드에는 **전송되지만 화면에서 안 쓰이는 필드(dead payload)** 와 **호출되지 않는 계산 함수**가 다수.

두 에이전트의 의견은 대부분 일치했고, 상충 지점은 사실상 한 곳(4-G, 집행 서브탭의 스택바 vs 비율바)뿐이다. 아래 주제별로 정리한다. 각 항목은 **[디자이너]** / **[frontend-dev]** / **[PM 판단]** 을 구분 표기한다.

---

## 주제 1 — 색상: 단계 hue는 깨끗하나 "상태 톤"이 단계색과 충돌

### 1-A. good/po 색 충돌 (두 에이전트 완전 일치)
- **[frontend-dev] Before(코드 사실)**: `theme/tokens.css`에서 `--tone-good-border: rgba(20,40,160,0.28)`와 `--tone-po-border: rgba(20,40,160,0.32)`는 **RGB가 완전히 동일(#1428A0)**, alpha만 0.28 vs 0.32 차이. 시각적으로 구분 불가.
  - `tone:'good'` 사용처: `DashboardView.vue:120`, `StatusDetailView.vue:326-328,339,349,350,360` 등 6개 카드.
  - `tone:'po'` 사용처: `DashboardView.vue:117`, `StatusDetailView.vue:322,337,338,347,348`.
  - 톤 시스템에 **녹색 good이 없음** — 그린(#059669)은 오직 `tone-execution` 전용.
- **[디자이너] 문제**: 하나의 채널(좌측 8px 바)에 "단계 정체성"과 "건강도"라는 **두 의미**가 실림. good=블루라 "긍정/정상"과 "품의 단계"가 구분 안 됨. 그린 카드가 "좋음"인지 "집행 단계"인지 혼동.
- **[디자이너] After**: **hue = 단계 정체성 전용, 영구히.** 건강도는 다른 채널(작은 상태 점/값 텍스트 색)로 분리하고 **good은 무장식**(정상은 경보 불필요 → 블루-good 충돌도 즉시 소멸). warn=앰버, bad=레드만 예외 표시(작은 점/칩). `MiniKpiGrid.vue`를 `stage?: po|contract|execution|total`(좌측 바)과 `status?: warn|bad`(코너 점) **두 prop으로 분리**, colored `good` 제거.

### 1-B. 같은 지표가 탭마다 hue가 바뀜 (디자이너 강조, frontend-dev 확인)
- **[디자이너] Before**: `계약전환율`이 `StatusDetailView.vue` overviewCards에선 `tone:'contract'`(퍼플, line 323), 같은 화면 contractCards에선 `s.contract_conversion_rate>=80 ? 'good':'warn'`(블루/앰버, line 349)로 렌더. `금액집행률`도 동일(execution 그린 vs good/warn 블루/앰버, line 360). → **같은 숫자가 한 카드에선 퍼플, 두 줄 아래선 블루** 라 사용자가 "퍼플=계약"을 학습할 수 없음.
- **[frontend-dev] 확인**: 톤 값 근거가 두 시스템(stage vs good/warn)에서 병렬로 오는 구조라 위 flip이 코드상 실재.
- **[디자이너] After**: 전환율/집행률 카드는 **양 탭에서 단계 hue 고정**(contract=퍼플, execution=그린), ≥80/≥70 임계 판정은 `status` 점 채널로 이동.

### 1-C. 리터럴 색 홀드아웃 (두 에이전트 일치)
- **[frontend-dev] Before**:
  - `DetailTable.vue:150` — 집행률 progress-fill이 `var(--samsung-blue)`(블루). **집행 지표인데 품의색.** 이번 조사에서 가장 명백한 색-의미 충돌.
  - `DiagnosisTable.vue:86-88` — `.stage-badge`가 `--blue-step-1` bg + `--samsung-blue` text로 **무조건 블루**. row.stage가 품의지연/계약대기/집행대기/잔여집행 어느 것이든 전부 블루 → 단계색으로 코딩할 무료 기회를 버리고 품의 블루와 재충돌.
- **[디자이너] After**: `DetailTable` 집행률 바 → `--stage-execution-color`(그린); `DiagnosisTable` 배지 → `row.stage` 기준 단계색(품의지연→블루 soft, 계약대기→퍼플 soft, 집행대기→그린 soft).

### 1-D. 중복/레거시 토큰 & 다크모드 잠복 버그 (frontend-dev 단독 발견, 기술적으로 중요)
- **[frontend-dev]**: `tokens.css`에 **동일한 #1428A0로 수렴하는 변수 5개**(`--samsung-blue`, `--blue-step-3`, `--executed-color`, `--stage-po-color` 등). 다크테마 override 블록(lines 43-47)은 **`--stage-*`만 remap**하고 `--samsung-blue`/`--executed-color`/`--blue-step-*`/`--tone-*`은 remap 안 함.
  - 결과: `SidebarFilters.vue`가 한 곳은 `--stage-po-color`(254,272), 다른 곳은 `--samsung-blue`(402-403)를 써서, **다크모드 전환 시 앞은 재색상, 뒤는 안 됨** — 계획된 프레젠테이션 다크모드의 사전 잠복 버그. `OrgButtonFilter.vue:41-42`(samsung-blue) vs `App.vue:109`(stage-po-color)도 동일.
  - `--executed-color: #1428A0`(블루)는 이름은 "집행"인데 값은 블루 → 집행=그린과 정면 모순. 미래 기여자가 파란 "executed" 색을 집기 쉬움.
- **[frontend-dev] 기타 리터럴**: 표 헤더 `#f1f5f9`가 5개 표 파일에 각각 리터럴로 복붙(`DetailTable:122`, `StageDetailTable:70`, `DiagnosisTable:65`, `OrgManagementTable:53`, `SimpleRecordTable:72`), tokens.css에 미정의. API 에러 텍스트 레드가 `#dc2626`(DashboardView:180, StatusDetailView:430)로 `--tone-bad-border` 레드와 별개.
- **[PM 판단]**: 1-D는 **다크모드 스펙(계획서 명시)과 직결된 실질 버그**라 우선순위를 낮게 볼 수 없다. 단계색 통합 작업(1-A~1-C)을 할 때 **레거시 토큰(`--executed-color`/`--blue-step-*`/중복 blue) 정리를 같은 PR에 묶는 것**을 권고. 단, 이는 색 코드 변경이 아니라 "동일 색으로 수렴하는 별칭 정리"이므로 톤앤매너 유지 전제와 충돌하지 않는다.

**주제 1 종합(PM)**: 색상 문제의 본질은 "새 색이 필요"가 아니라 **"하나의 채널이 두 의미를 짊어짐"**. 디자이너의 "hue=단계 전용 / good=무장식 / 상태=별도 점 채널" 원칙이 정확한 해법이고, frontend-dev의 코드 근거(같은 RGB, 다크 remap 누락)가 이를 뒷받침한다. **가장 오해를 유발하는 항목이라 1순위.**

---

## 주제 2 — 타이포그래피: 공유 스케일 부재, 위계 충돌

### 2-A. 상단 위계 붕괴 (두 에이전트 일치)
- **[frontend-dev] Before(코드)**: 전역 역할은 `tokens.css`에만 정의 — `.small-title` 1.4rem(61), `.big-title` 2.4rem(67), `.desc` 0.85rem(75), `.section-title` **1.4rem(81) ← small-title과 동일값**, `.chart-subtitle` 1.05rem(88).
- **[디자이너] 문제**: 팀명 eyebrow(`small-title`)와 콘텐츠 섹션 헤더(`section-title`)가 같은 1.4rem이라 페이지 레벨감이 평평. 레퍼런스는 "A-Infra기술팀"을 섹션 헤더보다 훨씬 작은 조용한 eyebrow로 둠.

### 2-B. "큰 숫자" 티어 불일치 (두 에이전트 일치)
- **[frontend-dev] Before**: `MiniKpiGrid.vue .kpi-value` = `1.7rem`(100) vs `StageFunnelCard.vue .funnel-pct` = `clamp(1.4rem,2vw,2rem)`(60). **같은 개념(헤드라인 숫자)을 fixed rem vs clamp() 두 방식**으로.
- **[디자이너]**: 퍼널 %가 KPI 값보다 큰 것 자체는 레퍼런스상 맞음(퍼널 %가 히어로). 다만 **의도된 명명 티어**여야지 두 값의 우연이면 안 됨.

### 2-C. 표 본문 4종 크기 + 라벨/캡션 난립 (두 에이전트 일치)
- **[frontend-dev] Before**: 시각적으로 같은 표 패턴인데 본문 크기가 4종 — `DetailTable/StageDetailTable` 0.78rem, `SimpleRecordTable` 0.8rem, `DiagnosisTable` 0.82rem, `OrgManagementTable` 0.85rem(각 파일 리터럴, th/td 패딩도 복붙 미세 상이). "작은 라벨/캡션" 역할이 0.7~0.9rem에 공유 토큰 없이 산재. **0.85rem이 8회+로 사실상의 표준이지만 우연** — 변경하려면 파일마다 손대야 함.

### 2-D. After — 7단계 스케일을 토큰으로 1회 정의 (디자이너 제안)
| 역할 | 토큰(신규) | 값 | 적용 |
|---|---|---|---|
| 페이지 제목 | `--fs-title` | 2.4rem/800 | `.big-title`(유지) |
| 섹션(H2) | `--fs-h2` | **1.5rem/750** | `.section-title`(1.4→1.5로 부제와 분리) |
| Eyebrow | `--fs-eyebrow` | **1.05rem/600** | `.small-title`(1.4→1.05로 낮춤) |
| 부제(H3) | `--fs-h3` | 1.05rem/700 | `.chart-subtitle` |
| 히어로 숫자 | `--fs-hero` | 2.0rem/800 | `StageFunnelCard` % |
| KPI 숫자 | `--fs-metric` | 1.7rem/800 | `MiniKpiGrid` 값 |
| 라벨 | `--fs-label` | 0.85rem/700 | kpi/funnel/ratio 라벨(0.82/0.85/0.90 통합) |
| 표 본문 | `--fs-table` | 0.82rem | 전 표(4종 통합), 초광폭 `StageDetailTable/DetailTable`만 dense 0.76rem |
| 캡션 | `--fs-caption` | 0.75rem | kpi-caption, ratio 라벨, funnel 분수 |

- **[PM 판단]**: 토큰화 자체는 리스크 낮고(값은 대부분 현행 유지), 후속 유지보수 이득이 큼. **논쟁 여지가 있는 건 값 변경 2건뿐** — `small-title` 1.4→1.05, `section-title` 1.4→1.5. 이 2건만 A/B로 오너 확인하고 나머지 토큰화는 안전하게 진행 가능.

---

## 주제 3 — 차트/테이블 비율: 산재한 높이값 + 2열 높이 불균형

### 3-A. 높이값이 공유 상수 없이 리터럴 (frontend-dev 코드 사실)
- **[frontend-dev]**: `EChart.vue` 기본 height 320px(17). `OrgIntegratedProgressChart.vue:4`·`MonthlyComboChart.vue:4` 모두 `height="340px"` 리터럴. `OrgStackedBarChart.vue`는 height 미전달→320 폴백(**단, 아무 뷰도 import 안 하는 dead code**). `StageFlowChart.vue`는 EChart가 아니라 `InlineRatioBar` div 리스트(콘텐츠 구동, 고정높이 없음).
  - 표: `DetailTable` max-height 640(106), `StageDetailTable` 380(55), `DiagnosisTable` 300(50). **`OrgManagementTable`·`SimpleRecordTable`은 max-height/overflow 미설정 → 행수만큼 무제한 성장**(SimpleRecordTable은 StatusDetail에서 4개 월별 표에 재사용, 각 12행 풀렌더 → 다른 표는 캡+스크롤인데 이것만 불일치).
  - 순: 차트 높이 3종(340/340/320) + 표 캡 3종(640/380/300) + 무제한 2개, 모두 컴포넌트-로컬 리터럴.

### 3-B. 상세 탭 2열 높이 불균형 (디자이너 관점)
- **[디자이너] 문제**: 각 서브탭이 `ratio-list`(~150px, 좌, `1fr`)와 `MonthlyComboChart`(340px, 우, `1.6fr`)를 쌍으로 둠 → 좌측이 더 좁고 높이도 절반 이하 → 비율바 아래 **큰 죽은 여백**. `.two-col`에 `align-items` 미지정. 레퍼런스는 좌우를 대략 등높 블록으로 둠. 퍼널 트랙 0.55rem은 2.0rem 히어로 % 대비 **저체중**.
- **[디자이너] After**: `.two-col`에 `align-items:stretch` + `.ratio-list`/`.stage-flow-list`를 `flex-column; justify-content:center; min-height:340px`로 페어와 등높 정렬. 컬럼 비율 `1fr 1.6fr` → **`1fr 1.4fr`**(우측 차트 60% 과폭 완화, 좌측 라벨 `인프라DT_PJT` 여유 확보, `.ratio-label` 110→120px). 퍼널 트랙 0.55→**0.75~0.8rem**. `--chart-h:340px` 토큰 도입으로 높이 협응. Dashboard `DiagnosisTable` max-height 300→340로 행 리듬 정렬.
- **[PM 판단]**: 3-A(토큰/무제한 표 캡)와 3-B(2열 정렬)는 방향이 일치·상보적. **무제한 성장 표 2개에 캡 부여**는 버그성이라 우선. `align-items:stretch`+`min-height`는 상세 탭에서 체감 가장 큰 "어긋남"을 제거하는 저비용 변경.

---

## 주제 4 — 중복 및 필요성: 퍼널·진단표·전환율이 2~4회 반복 + 백엔드 dead payload

### 4-A. StageFlowChart가 양 탭에 동일 (두 에이전트 일치)
- **[frontend-dev]**: `stage_flow`(`calc/stage.py:stage_flow_data`)를 `dashboard.py:62`·`status_detail.py:67`이 동일 전송, `DashboardView.vue:40`·`StatusDetailView.vue:54`가 **같은 `StageFlowChart` 컴포넌트**로 렌더. 상세 탭에선 `StageFunnelCard` 3장 **바로 아래**에 놓여 퍼널 개념을 연속 2회 표시.
- **[디자이너] 권고**: **탭별로 차별화, 상세 탭의 중복 인스턴스 제거.** `StageFunnelCard` 트리오(단계→단계 전환율+분수+바)가 더 풍부·레퍼런스 정합적이고 이 탭의 정체성. 상세에서 `StageFlowChart` 드롭, Dashboard에만 "전체대비" 컴팩트 개요로 유지(수식이 다름: 각 단계 vs 전체). 결과: Dashboard=전체대비 글랜스 / 상세=단계간 전환, 각 탭 퍼널 1개씩·목적 구분.

### 4-B. DiagnosisTable가 양 탭에 (두 에이전트 일치)
- **[frontend-dev]**: `make_bottleneck_table`(`stage.py:135`)이 `priority_actions`(dashboard.py:55)·`bottleneck`(status_detail.py:68) 둘의 원천. `make_priority_action_table`(`stage.py:198-206`)은 **독립 계산이 아니라 bottleneck에 `priority` 키만 추가·재정렬**. `DashboardView.vue:46`(top10)·`StatusDetailView.vue:60`(top12)이 같은 `DiagnosisTable`로 렌더 — 절단/정렬만 다름. **게다가 `types/api.ts:57 DiagnosisRow.priority`는 백엔드가 채우지만(`stage.py:203`) `DiagnosisTable.vue` 템플릿은 절대 읽지 않음 → dead field.**
- **[디자이너] 권고**: 둘 다 유지하되 **범위·라벨 차별화.** Dashboard = 짧은 "즉시 조치 Top 5" + 순위 컬럼(현재 안 쓰이는 `priority`를 여기서 살림), 상세 = 전체 진단 리스트(감사용). 지금은 동일해 보여 데자뷰 유발.
- **[PM 판단]**: `priority` 필드가 이미 백엔드에 있는데 프론트가 안 씀 → 디자이너의 "Dashboard에 순위 컬럼" 제안이 **새 백엔드 작업 없이** dead field를 되살리는 정합적 해법. 채택 시 삭제가 아니라 활용 방향.

### 4-C. 전환율 3종이 각 최대 4회 (두 에이전트 일치)
- **[디자이너]**: `품의완료율`이 Dashboard exec KPI(117), StatusDetail overview KPI(322), `StageFunnelCard`(30), po 서브탭 KPI(339) **4곳**. 계약전환율·집행률도 동일 패턴.
- **[디자이너] 권고**: **StatusDetail 내에서 overview `MiniKpiGrid`의 3개 전환율 카드를 제거**하고 `StageFunnelCard` 트리오가 소유. overview 8-KPI(322-330)와 퍼널 카드(26-47)가 지척에서 같은 3% 반복 → overview는 퍼널이 안 보여주는 4개(품의지연/계약대기/집행대기/잔여집행)만 남겨 **8칸→4칸 리스크 행**으로 집중. (Dashboard exec KPI가 전환율 유지하는 건 OK — 랜딩 요약이고 사용자가 두 탭을 동시에 보지 않음.)

### 4-D. MonthlyComboChart 4회 (두 에이전트 일치) — 유지
- **[디자이너]**: Dashboard(누적품의+누적집행)와 3개 서브탭 각각. 개요=단계 합성, 서브탭=단일 단계 드릴 → **정당한 차별화, 유지.** Dashboard 콤보는 3서브탭 차트의 상위집합 프리뷰임을 인지만.

### 4-E. 하단 "월별 비교 테이블"이 3서브탭 월별표와 중복 (디자이너)
- **[디자이너]**: `StatusDetailView.vue:268-283`가 po/contract/execution 월별 `SimpleRecordTable`의 합집합(+심의진행건수 1컬럼 추가). **순수 중복은 아님(심의진행건수 추가)** → 삭제보다 **"월별 전체 데이터 보기" 토글로 접기** 권고(하단 3번째 풀폭 표로 경합하지 않게).

### 4-F. Dashboard 내부: org_progress 차트+표 병치 (frontend-dev 지적) — 유지
- **[frontend-dev]**: `data.org_progress`(`org.py:95`)를 `OrgIntegratedProgressChart`(55)와 `OrgManagementTable`(78)로 같은 화면 연속 2회.
- **[디자이너]**: 차트=스캔, 표=정확값의 **정당한 페어링, 유지**(중복 아님).

### 4-G. dead component `OrgStackedBarChart.vue` — ★ 유일한 의견 상충 지점
- **[frontend-dev] 사실**: `OrgStackedBarChart.vue`를 **어떤 뷰도 import 안 함(zero import site).** 집행 서브탭(`StatusDetailView.vue:207-224`)은 대신 `InlineRatioBar` 수동 루프(`execution_monitoring.org_table`)를 씀.
- **[디자이너] 의견**: 삭제 **또는** 집행 서브탭에서 재채택 중 택1. 선행 2026-07-17 리뷰 §3-5는 "집행은 집행/미집행 두 금액 대비라 스택바가 InlineRatioBar보다 정보량이 많다"고 논증했었음 → **재채택(그린 스택)도 유효**.
- **★ 상충 지점**: 선행 리뷰의 설계 의도(집행=스택바 유지)와 현재 구현(집행=InlineRatioBar로 이관)이 **엇갈렸다.** frontend-dev는 "현재 dead"라는 사실만, 디자이너는 "삭제 vs 재채택" 두 갈래를 제시.
- **[PM 판단]**: 이건 순수 코드정리가 아니라 **정보설계 결정**이다. 집행 단계에서 "집행률(비율 1개)"만 보여줄지 "집행/미집행(두 금액)"을 보여줄지는 업무상 무엇이 관리 포인트냐의 문제. 오너 확인 필요 항목으로 올린다. 결정 전까지 dead 컴포넌트를 **삭제하지 말고 보류**(재채택 시 되살려야 하므로). → 아래 결정 체크리스트 #4.

### 4-H. 백엔드 dead payload / 미호출 함수 (frontend-dev 단독, 기술 심층)
- **[frontend-dev] 발견**:
  1. `dashboard.py:9`이 `calc/kpi.py`의 `calculate_kpi_values`를 **import하지만 호출 안 함** — 완전 dead. 게다가 그 함수(`kpi.py:10-28`)는 이미 별도로 만드는 `executive_kpi` dict(dashboard.py:45-52)와 total_count/invest_sum/amount_execution_rate가 겹침.
  2. `helpers.py:202 make_invest_signal`은 **어디서도 호출 안 됨**(zero call site). `detail.py:39-47`이 동일 로직을 `_signal()`로 재구현. **dead 중복 함수.**
  3. `monthly_compare_records`(`monthly.py:207`)가 ~23컬럼 반환(사전변환 `_억원` 5종 + 예측 3종 포함). Dashboard `monthly_flow`(124-146)는 4컬럼만, StatusDetail `monthly_compare`(268-283)는 11컬럼만 읽음. **예측 컬럼(`기성금액_예측`/`누적기성금액_예측`/`예측누적집행률`)은 양 탭 어디서도 렌더 안 됨.** `_억원` 사전변환 컬럼도 프론트가 안 쓰고 오히려 프론트가 raw-won에서 `toEok()`/`formatMoney()`로 **재계산**(서버·클라 2중 계산).
  4. `MetaResponse.current_month`(`meta.py:26`, `types/api.ts:10`)는 정의되지만 `App.vue`는 `current_label`만 읽음 → **미사용.**
- **[PM 판단]**: 4-H는 화면엔 안 보이지만 **페이로드 비대·이중계산·혼란 유발**. No-DB·Replica=1 구조에서 성능 병목은 아니나(선행 라운드 backend-dev 확인), **유지보수 관점 정리 가치**가 있다. 단, **예측 컬럼 삭제는 신중히** — 향후 "예상 연말 집행률" 등 예측 시각화를 되살릴 여지가 있으므로(레거시에 존재), 삭제가 아니라 **"현재 미사용"으로 명시 후 보류**를 권고. `calculate_kpi_values` 미사용 import·`make_invest_signal` dead 중복은 **안전 삭제 후보**.

**주제 4 종합(PM)**: 상세 탭이 가장 과밀하다(퍼널 2회 + 전환율 3종 4회 + 진단표 + 월별표 중복). 디자이너의 "상세에서 StageFlowChart 드롭 + overview KPI를 4개 리스크 카드로 축소"가 **가장 큰 정리 효과**. 백엔드 dead payload는 별개 트랙(안전 삭제 vs 보류)으로 분리 처리 권고.

---

## 의견 일치/상충 요약 (PM)

| 항목 | ui-designer | frontend-dev | 상태 |
|---|---|---|---|
| OrgStackedBarChart dead | 삭제 or 집행탭 재채택 | 어떤 뷰도 미import(사실) | **상충 아님, 결정 필요(4-G)** |
| good/po 색 동일 | 채널 분리 제안 | 동일 RGB 확인 | 일치 |
| DetailTable 집행률=블루 | 그린으로 | samsung-blue 리터럴 확인 | 일치 |
| 전환율 hue flip | 강하게 문제제기 | 톤 근거 병렬 확인 | 일치 |
| 타이포 스케일 부재 | 7단계 토큰 제안 | 산재값 목록화 | 일치 |
| 차트/표 높이 산재 | 2열 정렬·비율 제안 | 리터럴/무제한 확인 | 일치(상보) |
| 백엔드 dead payload | (미다룸) | 상세 발굴 | frontend-dev 단독 |
| 다크모드 토큰 remap 누락 | (미다룸) | 잠복 버그 발굴 | frontend-dev 단독 |

유일한 실질 상충은 **4-G(집행 서브탭 스택바 vs 비율바)** 이며, 이는 디자인 취향이 아니라 **정보설계 결정**이라 오너 판단 사항으로 올린다.

---

## 실행 우선순위 (PM 권고, 오너 확정 전 제안)

1. **[색상 1순위·오해 유발]** `MiniKpiGrid` 톤을 `stage`+`status`로 분리, colored good 제거, 전환율/집행률 탭간 hue 고정 (주제 1-A,1-B). 영향: `MiniKpiGrid.vue`, `DashboardView.vue`, `StatusDetailView.vue`.
2. **[색상·소]** `DetailTable` 집행률 바 그린화, `DiagnosisTable` 배지 단계색화 (1-C). + 레거시/중복 blue 토큰 정리 & 다크 remap 누락 보정 (1-D, 다크모드 스펙 직결).
3. **[중복 정리·체감 큼]** 상세 탭 `StageFlowChart` 드롭 + overview KPI를 4개 리스크 카드로 축소 (4-A,4-C). `priority` dead field를 Dashboard 순위 컬럼으로 활용 (4-B).
4. **[타이포]** 7단계 스케일 토큰화 + `small-title`/`section-title` 위계 분리 (주제 2). 값 변경 2건만 오너 A/B 확인.
5. **[비율]** `.two-col align-items:stretch` + 좌측 비율카드 `min-height:340px`, 퍼널 트랙 굵게, `1fr 1.4fr`, 무제한 표 2개 캡 부여 (주제 3).
6. **[정리]** `calculate_kpi_values` 미사용 import·`make_invest_signal` dead 중복 안전 삭제, `OrgStackedBarChart`는 4-G 결정까지 보류 (4-G,4-H).

모두 **품의-블루 / 계약-퍼플 / 집행-그린 언어 안에서** 진행되며 새 팔레트를 도입하지 않는다. 전부 SPA 내부 변경 + 백엔드 dead-code 정리 수준으로, plan_v5 3단계(로컬 화면 완성) 범위와 충돌 없다(Replica=1·PVC·Nginx 역할·인증 범위 등 기존 제약 무관).

---

## 오너 결정 필요 항목 (체크리스트)

1. **주제 1 채택 여부**: KPI 톤을 stage/status 2채널로 분리하고 colored good 제거 (PM 권고: 채택 — 가장 오해 유발).
2. **레거시 토큰 정리 범위**: `--executed-color`/`--blue-step-*`/중복 blue를 이번에 함께 정리할지 (PM 권고: 다크모드 버그 직결이므로 색상 작업과 동일 PR).
3. **상세 탭 슬림화 강도**: StageFlowChart 드롭 + overview 8→4 KPI (PM 권고: 채택) / 부분만 / 현행 유지 중.
4. **★ 집행 서브탭 표현(4-G)**: (a) InlineRatioBar 유지 + `OrgStackedBarChart` 삭제 / (b) 스택바 재채택(그린, 집행/미집행 두 금액) — **정보설계 결정, 오너 판단 필요.**
5. **타이포 값 변경 2건**: `small-title` 1.4→1.05, `section-title` 1.4→1.5 A/B 확인 여부.
6. **백엔드 dead payload 처리**: 안전 삭제(미사용 import·dead 함수) vs 예측 컬럼 보류(향후 예측 시각화 대비) 구분 승인.

**PM 요약 권고**: 1(색상 채널 분리) → 3(상세 슬림화) → 2(레거시 토큰+다크 버그) → 4·5(타이포/비율)를 순차로. 4-G와 백엔드 예측 컬럼만 "삭제 전 오너 확인"으로 잠그면 리스크가 가장 균형 잡힌다. 최종 선택은 오너 몫이다.
