# 2026-07-22 대시보드 "박스형 패널 통일" 검토 (계획 전용, 코드 미변경)

- 대상 화면: `frontend/src/views/DashboardView.vue` (투자 종합현황)
- 성격: **순수 검토/계획 라운드. 이번 라운드는 코드를 수정하지 않는다.** 실제 구현은 오너 승인 후 별도 라운드에서 진행.
- 참여: ui-designer(디자인 의견) + frontend-dev(기술 조사) + pm-coordinator(종합).
- 결론 한 줄: **"박스를 늘리자"가 아니라 "이미 3종류로 섞여 있는 그릇을 1종류(`.card`)로 통일하자"가 정확한 프레이밍이다. 요청 2·3(차트/표 박스화)은 권장, 요청 1(퍼널 행 간격만 확대)은 디자이너·프론트 모두 방법을 바꿔서 하기를 권고.**

---

## 0. 사전 정정 (PM 확인 사항)

ui-designer가 "`docs/design-refs/` 이미지와 직전 리뷰 문서가 이 clone에 없다"고 보고했으나, **실제로는 존재한다.**

- 존재 확인: `docs/design-refs/KakaoTalk_20260717_165720199.png`, `..._01.jpg`, `..._02.jpg`
- 존재 확인: `docs/design-review/2026-07-21-priority-cards-review.md`, `2026-07-20-design-upgrade-review.md` 등

→ ui-designer의 **구조 판단(그릇 통일)은 코드만으로 확정 가능하므로 그대로 유효**하다. 다만 ui-designer가 "이미지 부재로 색/다크 표면값은 재대조 필요"라고 단 유보 조건은 **전제가 틀렸으므로**, 실제 구현 라운드 전에 이미지 3장을 직접 대조해 다크/색 판단을 확정할 수 있다(별도 차단 요인 아님).

---

## 1. 현재 상태 (코드 기준 사실)

한 화면에 동급 콘텐츠가 **3가지 서로 다른 그릇**에 담겨 있다:

| 그릇 | 스펙 | 적용 요소 |
|---|---|---|
| A. 완전 패널 | `bg + border 1px + shadow + radius 1rem + padding` | `StageFlowChart(.stage-flow-list)`, `PriorityCardList(.priority-cards)`, `StatusDetailView(.ratio-list)` |
| B. 맨 캔버스 | 그릇 없음. page-bg 위 EChart 340px 직접 | `OrgIntegratedProgressChart`, `MonthlyComboChart` |
| C. 실선 테두리만 | `border 1px + radius 0.7rem` (bg/shadow 없음) | `OrgManagementTable(.table-wrap)`, `DetailTable(.table-wrap)` |

추가 사실:
- `tokens.css:98-104`에 전역 `.card` 유틸리티 클래스(`bg/border/radius/shadow/padding:1rem`)가 **이미 정의돼 있으나 현재 아무 데서도 쓰이지 않는 죽은 코드**다. A그룹 3곳은 이 `.card`와 거의 동일한 CSS를 **각자 scoped로 복붙**(padding만 `1.1rem 1.2rem`으로 미세하게 다름)하고 있다.
- 시선 동선상 (2)행(무거운 흰 박스 2개) 바로 아래 (3)행이 **그릇 없이 붕 뜬 차트 2개** → 페이지 중앙에 "바닥이 빠진 구간"이 생긴다. **이것이 현재 가장 거슬리는 지점**이며, 요청 2가 정확히 이걸 해소한다.
- 다크(프레젠테이션) 테마: `tokens.css:47-51`은 **stage 색 3개만** 오버라이드하고, 표면 토큰(`--card-bg/--page-bg/--border-color/--shadow/--neutral-soft`)의 다크값은 없다. 단, 같은 파일 주석이 "다크 스위치(`/present`) 배선은 다음 라운드"라고 명시 → 지금 당장 해결 대상은 아니나, 박스를 구조 모티프로 확정하면 **그 라운드에서 반드시 표면 토큰 세트가 같이 정의돼야** 흰 박스가 프레젠테이션 화면에서 깨지지 않는다.

---

## 2. 요청별 결론 (디자이너 · 프론트 종합)

### 요청 1 — "전체 진행 퍼널"과 "관리 필요" 박스 높이 맞추기 (사용자안: `InlineRatioBar` 4행 세로 간격 확대)

- **디자이너 의견: 사용자안(간격만 확대)은 채택하지 말 것.** 얇은 28px 바 4개의 간격만 벌리면 "가느다란 선 4개가 넓은 여백에 둥둥" → 정확히 우려하던 "빈 공간 과다"가 현실화. 잉크는 그대로인데 여백만 늘어나는 최악 케이스.
  - 대안 조합: (1) **바 두께 상향** `track-height 28px → 36~40px` (가장 효과 큼, 공간을 여백이 아닌 실체로 채움 + inside 라벨 가독성↑), (2) `.stage-flow-list`를 `flex column + justify-content:space-between` + 패널 `height:100%`로 여백을 상하 대칭 분배, (3) `.two-col` 셀을 `flex column`으로 등높이 배선. 그래도 높이차가 크면(대략 120px 초과) **짧은 쪽을 늘리기보다 긴 쪽(`PriorityCardList`의 `VISIBLE_CARDS 4→3`)을 줄여** 맞추는 게 항상 안전.
- **프론트 의견(구현 안전성 관점):** 만약 오너가 그래도 "행 간격 확대"를 원하면, **`trackHeight` 선례와 동일한 옵셔널 prop(`rowGap` 류)** 을 `InlineRatioBar`에 추가하고 `StageFlowChart`가 중계, `DashboardView` 호출부에서만 값 지정하는 방식이 가장 안전(미지정 시 기존 동작 100% 보존 → `StatusDetailView`의 공용 사용처 무영향). 단순 인라인 `margin-bottom`은 `.ratio-row:last-child{margin-bottom:0}`를 덮어써 하단 여백이 생기므로, `margin-bottom: var(--row-gap,1rem)` + `:not(:last-child)` 방식으로 구현해야 함.
- **PM 종합:** 두 의견은 상충이 아니라 **역할 분담**이다. 디자이너 = "간격만 늘리는 미학은 나쁘니 두께+분배로 가라", 프론트 = "어떤 방식이든 공용 컴포넌트 안 건드리려면 옵셔널 prop으로". → **권고: 1차로 `track-height 36px` + space-between + 등높이 배선(디자이너 대안). 그래도 부족하면 `VISIBLE_CARDS 4→3`. '행 간격 확대'는 채택 시 옵셔널 prop으로만.** (아래 체크리스트 D-1에서 오너 결정.)

### 요청 2 — "조직별 종합 진행률" · "월별 핵심 진행 흐름"도 흰 박스로 통일

- **디자이너: 권장.** 단 핵심은 "박스를 많이"가 아니라 "**한 종류 박스로**". 그릇 treatment(같은 hairline border, 같은 옅은 shadow, 같은 radius/padding)가 동일하면 박스가 6개여도 "정렬된 카드 그리드"로 차분하게 읽힌다. 무거워 보이는 원인은 개수가 아니라 강도 불일치. 현재 shadow 토큰이 이미 충분히 옅어 통일만 하면 무거워지지 않음. → (3)행의 "바닥 빠짐" 해소.
- **프론트(기술 확인):** 순수 ECharts를 바깥 패딩 박스로 감싸도 **grid margin·height 재조정 불필요**. `EChart.vue`가 resize마다 컨테이너 실측을 다시 읽어 렌더하므로 잘림 없음. 다만 카드 패딩만큼 폭이 줄어 좁은 랩톱에서 y축 타이틀/바깥 라인 라벨이 테두리에 살짝 붙어 보일 수 있어 구현 후 육안 확인 정도만 필요.
- **⚠ 프론트가 잡은 교차 화면 충돌(중요):** `MonthlyComboChart`는 `DashboardView`뿐 아니라 **`StatusDetailView`에서 3번(품의/계약/집행 탭) 더 사용**된다. 따라서 **`MonthlyComboChart.vue` 컴포넌트 루트에 `class="card"`를 박으면 안 된다** — 그러면 이번 범위 밖 화면 3곳이 의도치 않게 바뀐다. **반드시 `DashboardView` 호출부에서 `<div class="card"><MonthlyComboChart/></div>`로 감쌀 것.** 일관성을 위해 `OrgIntegratedProgressChart`(단일 사용처라 내부에 넣어도 안전)도 **동일하게 호출부 래핑으로 통일** 권장.

### 요청 3 — "조직별 종합 관리 테이블" · "상세 리스트"도 박스화 (이중 테두리 문제)

두 에이전트 모두 "테이블을 별도 `.card`로 **또 감싸는 것**은 금지(테두리 안 테두리)"에 합의. **접근이 두 갈래로 갈린다:**

- **디자이너안(옵션3, 저비용): in-place 승격.** 바깥 래퍼를 두르지 말고 기존 `.table-wrap`에 `background + box-shadow`만 추가하고 `radius`를 `1rem`으로 올려 통일. **border는 1겹 그대로 유지** → 이중 테두리 원천 차단, 래퍼 추가 0.
- **프론트안: 바깥 `.card` 래핑 + 내부 테두리 제거.** `<div class="card">`로 감싸고 `.table-wrap`의 `border/border-radius`를 제거(스크롤 속성 `overflow`/`max-height`는 유지). → "모든 콘텐츠는 `.card`" 일관성에 부합.
- **양쪽 합의된 기술 사실:** sticky 헤더(`DetailTable`)는 `.table-wrap`의 `overflow:auto`가 스크롤 컨테이너이므로, 바깥 `.card`(overflow 기본 visible)를 씌워도 **정상 동작**. 단 `.card`에 `overflow:hidden`을 넣지 말 것(불필요, sticky/radius 간섭 유발 소지).
- **PM 종합:** 결과물은 사실상 동일(단일 그릇 + 테두리 1겹). **`.card`를 화면 전 요소의 단일 소스로 밀 거면 프론트안(래핑+내부 제거)이 일관적, 최소 변경만 원하면 디자이너안(in-place 승격)이 저비용.** 체크리스트 D-3에서 오너 결정.

---

## 3. 공용화 방식 (요청 2·3 적용 시 같은 박스 CSS가 5~6곳 중복 문제)

- **프론트: 새 컴포넌트(`PanelCard.vue`) 만들지 말고 기존 전역 `.card` 유틸리티 재사용 권장.** 이 프로젝트는 이미 `.section-title` 등 CSS 유틸리티 컨벤션을 쓰고, 이 문제는 "로직 컴포넌트"가 아니라 "순수 시각 박스"라 컴포넌트 경계 신설은 과도한 추상화(이 프로젝트 원칙에 반함). `PanelCard`로 가면 순수 ECharts 리프까지 슬롯으로 감싸야 해 결합도만 올라감.
  - 방법: `class="stage-flow-list card"`처럼 병기하고 각 컴포넌트 scoped에서 `bg/border/radius/shadow/padding` 5개 속성 제거. padding 차이는 `.stage-flow-list.card { padding: 1.1rem 1.2rem }` **결합 선택자**로 오버라이드(소스 순서 의존 회피).
  - scoped 주의: 전역 `.card`는 자식 컴포넌트 어느 엘리먼트에 붙여도 정상 적용됨(scoped라 안 먹는 문제 없음). 다만 오버라이드를 각 컴포넌트 scoped에 흩어 두면 중복이 재발하므로 결합 선택자로 명시.
- **디자이너: 방향 동일(단일 소스로 흡수).** 단 요청3을 "옵션1(표를 패널 안에 flush)"로 갈 경우엔 `padding:0` 변형을 지원하는 `<Panel>` 컴포넌트가 있으면 이상적이라고 언급 → **여기서만 프론트와 미세한 온도차**(프론트는 컴포넌트화 반대). 프로젝트의 과잉 추상화 회피 원칙을 고려하면 **`.card` 유틸리티 재사용이 1순위**, `<Panel>` 컴포넌트화는 보류.

---

## 4. 예상 구현 프로세스 (승인 시, 파일 · 순서)

> 아래는 "이렇게 진행될 것"이라는 예측이며, 이번 라운드에서 실행하지 않는다.

1. **[토큰 정합]** `frontend/src/theme/tokens.css` — `.card`의 기본 `padding`을 현행 패널값(`1.1rem 1.2rem`)에 맞춰 통일(선택). 다크 표면 토큰은 이번엔 정의만 검토(실 배선은 `/present` 라운드).
2. **[중복 흡수]** `StageFlowChart.vue` / `PriorityCardList.vue` / `StatusDetailView.vue(.ratio-list)` — scoped 박스 CSS를 `.card` 병기로 치환(기능·외형 동일, 유지보수 단일화).
3. **[요청 2 — 차트 박스화]** `DashboardView.vue` (3)행 — `OrgIntegratedProgressChart`, `MonthlyComboChart`를 **호출부에서 `<div class="card">`로 래핑**. (컴포넌트 내부 수정 아님 → `StatusDetailView`의 콤보차트 3곳 무영향.)
4. **[요청 3 — 표 박스화]** `OrgManagementTable.vue` / `DetailTable.vue` — 오너가 고른 방식(in-place 승격 or 래핑+내부제거)으로 단일 그릇화. sticky/스크롤 속성 유지.
5. **[요청 1 — 높이 맞춤]** `DashboardView.vue`에서 `track-height 28→36px` + `.stage-flow-list` space-between + `.two-col` 셀 등높이. (필요 시 `PriorityCardList` `VISIBLE_CARDS 4→3`.) '행 간격 확대'를 채택하면 `InlineRatioBar` 옵셔널 `rowGap` prop 추가 + `StageFlowChart` 중계.
6. **[검증]** `npm run lint`, `npm run build`, 라이트 테마 육안 확인(좁은 폭 차트 라벨 붙음 여부), (다크 스위치 도입 라운드에서) 프레젠테이션 육안 확인.

의존 순서 핵심: **1·2(공용화) → 3·4(박스화) → 5(높이)**. 공용화를 먼저 해야 3·4에서 중복이 새로 생기지 않는다.

---

## 5. 예상 화면 변화

- (3)행 차트 2개가 흰 카드 위에 얹혀 (2)행과 같은 그릇이 되며 **페이지 중앙의 "바닥 빠짐" 구간 소멸** → 위→아래로 KPI줄 / 카드행 / 카드행 / 카드 테이블 / 카드 리스트가 **일관된 카드 리듬**으로 정렬.
- 표 2개가 얇은 테두리에서 **배경+옅은 그림자를 가진 패널**로 승격되어 나머지와 동급으로 보임(이중 테두리 없음).
- 좌측 "전체 진행 퍼널" 바가 28→36px로 도톰해지고 여백이 상하 대칭 분배되어 우측 "관리 필요" 박스와 **높이가 시각적으로 정렬**됨(빈 공간 느낌 최소화).
- KPI 6칸은 **그대로 유지**(이미 카드라 다시 감싸면 카드-인-카드로 무거워짐 → 감싸지 않음).
- 라이트 테마에선 즉시 개선. **다크(프레젠테이션)에선 표면 토큰이 없으면 흰 박스가 그대로 남아 깨짐** → 다크 스위치 도입 라운드에서 표면 토큰 세트가 반드시 동반돼야 함.

---

## 6. 상충 지점 정리

| # | 항목 | 디자이너 | 프론트 | PM 판단 |
|---|---|---|---|---|
| C1 | 요청1 방법 | 간격 확대 반대 → 바 두께+분배 | (원하면) 옵셔널 prop로 안전 구현 | 상충 아님. 두께+분배 우선, 간격확대는 prop으로만 |
| C2 | 공용화 | `.card` 흡수 or (flush 시) `<Panel>` | `.card` 재사용, 새 컴포넌트 반대 | `.card` 재사용 1순위(과잉추상화 회피 원칙) |
| C3 | 요청3 방식 | in-place 승격(저비용, border 1겹 유지) | 래핑+내부 테두리 제거(일관성) | 결과 동일. 오너 선택(저비용 vs 일관성) |
| C4 | 이미지 유무 | "없다"고 판단(오판) | 해당 없음 | 이미지 실재 → 다크/색은 재대조 가능 |

교차 화면 리스크(둘 다 상충 아님, 반드시 준수): **`MonthlyComboChart`·`InlineRatioBar`는 `StatusDetailView`와 공유** → 컴포넌트 내부를 바꾸면 범위 밖 화면이 변함. 반드시 **호출부(DashboardView) 한정**으로 적용.

---

## 7. 오너 결정 체크리스트

- [ ] **D-1 (요청1):** 퍼널/관리필요 높이 맞춤 방식 — (A) 바 두께 36px + space-between + 등높이 [디자이너·PM 권고] / (B) 여기에 `PriorityCardList` `VISIBLE_CARDS 4→3` 병행 / (C) 그래도 '행 간격 확대'를 원하면 옵셔널 `rowGap` prop 방식. 어디까지 채택?
- [ ] **D-2 (요청2 범위):** 차트 2개 박스화 진행 승인 여부. (진행 시 호출부 래핑 방식 고정 — `MonthlyComboChart` 컴포넌트 내부 수정 금지 확인.)
- [ ] **D-3 (요청3 방식):** 표 박스화 접근 — (A) in-place 승격(최소 변경) / (B) `.card` 래핑 + 내부 테두리 제거(일관성). 택1.
- [ ] **D-4 (공용화):** `.card` 유틸리티 재사용으로 확정할지(`<Panel>` 컴포넌트화 보류 확인).
- [ ] **D-5 (KPI):** KPI 6칸은 박스로 감싸지 않는다(현행 유지)에 동의?
- [ ] **D-6 (다크 스코프):** 박스를 구조 모티프로 확정 시 다크 표면 토큰(`--card-bg/--page-bg/--border-color/--shadow/--neutral-soft`) 정의를 **이번에 같이 넣을지 vs `/present` 스위치 도입 라운드로 미룰지**. (미루면 그때까지 다크는 미완성 상태 유지.)
- [ ] **D-7 (레퍼런스 재대조):** 실 구현 전 `docs/design-refs/` 이미지 3장으로 색/여백/다크 표면값을 재확인할지.

---

## 8. 참고 파일 경로

- `C:\dev\IMS_dev_clone\frontend\src\views\DashboardView.vue`
- `C:\dev\IMS_dev_clone\frontend\src\theme\tokens.css` (`.card` 98–104, 다크 오버라이드 47–51)
- `C:\dev\IMS_dev_clone\frontend\src\components\charts\StageFlowChart.vue` / `InlineRatioBar.vue` / `OrgIntegratedProgressChart.vue` / `MonthlyComboChart.vue` / `EChart.vue`
- `C:\dev\IMS_dev_clone\frontend\src\components\table\PriorityCardList.vue` / `OrgManagementTable.vue` / `DetailTable.vue`
- `C:\dev\IMS_dev_clone\frontend\src\views\StatusDetailView.vue` (`MonthlyComboChart` x3, `InlineRatioBar`/`.ratio-list` 공유 사용처)
- `C:\dev\IMS_dev_clone\docs\design-refs\` (레퍼런스 이미지 3장 — 실재함)
