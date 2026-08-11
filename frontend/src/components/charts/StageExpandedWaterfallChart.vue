<template>
  <div class="funnel">
    <div class="funnel-chart">
      <div class="funnel-axis">
        <div
          class="axis-total"
          :class="{ active: selectedKey === 'total' }"
          role="button"
          tabindex="0"
          @click="emit('select', 'total')"
          @keydown.enter="emit('select', 'total')"
        >
          <span class="axis-total-label">전체 투자계획</span>
          <span class="axis-total-value">{{ (totalItem?.count ?? 0).toLocaleString() }}건</span>
        </div>
        <div
          class="drop-chip"
          :class="{ active: selectedKey === 'drop' }"
          role="button"
          tabindex="0"
          @click="emit('select', 'drop')"
          @keydown.enter="emit('select', 'drop')"
        >
          <span class="lbl">Drop</span>
          <b class="val">{{ dropCount.toLocaleString() }}건</b>
        </div>
        <span class="axis-zero">0</span>
      </div>

      <div
        ref="plotRef"
        class="funnel-plot"
      >
        <div class="funnel-plot-baseline" />

        <!-- 진행 투자계획→심의 완료→계약 완료→투자 완료 칩 사이 화살표. 클러스터별 group-spacer
             유무로 칩 사이 실제 간격이 균일하지 않아(2026-08-11 디자이너 검토), 고정 CSS로는
             중앙 정렬이 안 돼 인접 칩의 실측 위치 중간점에 절대 배치한다. -->
        <div
          class="funnel-arrows"
          aria-hidden="true"
        >
          <span
            v-for="(pt, idx) in arrowPoints"
            :key="idx"
            class="chip-arrow"
            :style="{ left: pt.left + 'px', top: pt.top + 'px' }"
          >
            <svg
              width="62"
              height="10"
              viewBox="0 0 62 10"
            >
              <line
                x1="0"
                y1="5"
                x2="48"
                y2="5"
                stroke="var(--text-subtle)"
                stroke-width="2"
              />
              <path
                d="M48 1 L62 5 L48 9 Z"
                fill="var(--text-subtle)"
              />
            </svg>
          </span>
        </div>

        <div
          v-for="(cluster, clusterIdx) in clusters"
          :key="cluster.key"
          class="funnel-cluster"
        >
          <div class="funnel-bars">
            <div
              v-for="ci in cluster.items"
              :key="ci.item.key"
              class="funnel-bar-col"
              :class="{ 'wide-label': ci.item.key === 'irb_path', active: selectedKey === ci.item.key }"
              role="button"
              tabindex="0"
              @click="emit('select', ci.item.key)"
              @keydown.enter="emit('select', ci.item.key)"
            >
              <div
                class="funnel-bar"
                :class="{ narrow: ci.item.key === 'irb_path' }"
                :style="barStyle(ci)"
              />
              <div
                class="funnel-bar-value"
                :class="{ muted: ci.trailing }"
                :style="{ bottom: barHeight(ci.item) + 6 + 'px' }"
              >
                {{ ci.item.count.toLocaleString() }}
              </div>
            </div>
          </div>

          <div class="funnel-item-labels">
            <span
              v-for="ci in cluster.items"
              :key="`${ci.item.key}-label`"
              class="funnel-label"
              :class="{ 'wide-label': ci.item.key === 'irb_path', active: selectedKey === ci.item.key }"
              role="button"
              tabindex="0"
              @click="emit('select', ci.item.key)"
              @keydown.enter="emit('select', ci.item.key)"
            >
              <span
                v-for="(line, lineIdx) in labelLines(ci.item.label)"
                :key="lineIdx"
                class="label-line"
              >{{ line }}</span>
            </span>
          </div>

          <div class="funnel-group-row">
            <span
              v-if="cluster.groupLabel"
              :ref="(el) => setChipRef(el, clusterIdx)"
              class="group-chip"
              :class="{ active: selectedKey === cluster.groupLabel.key }"
              :style="{ background: cluster.groupLabel.wash }"
              role="button"
              tabindex="0"
              @click="emit('select', cluster.groupLabel.key)"
              @keydown.enter="emit('select', cluster.groupLabel.key)"
            >
              <span :style="{ color: cluster.groupLabel.color }">{{ cluster.groupLabel.label }}</span>
              <b :style="{ color: cluster.groupLabel.color }">{{ groupLabelCount(cluster.groupLabel.key).toLocaleString() }}건</b>
            </span>
            <span
              v-if="cluster.hasTrailing"
              class="group-spacer"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { ProgressFunnelItem } from '../../types/api'
import { STAGE } from '../../theme/stageColors'

const props = defineProps<{ items: ProgressFunnelItem[]; selectedKey?: string | null }>()
const emit = defineEmits<{ select: [key: string] }>()

const CHART_HEIGHT = 230

interface ClusterItem {
  item: ProgressFunnelItem
  trailing: boolean
}

interface GroupLabel {
  key: string
  label: string
  color: string
  wash: string
}

interface Cluster {
  key: string
  items: ClusterItem[]
  hasTrailing: boolean
  groupLabel?: GroupLabel
}

// "전체 투자계획" 막대는 없애고 y축 상단 라벨로 대체했지만(2026-08-09 오너 요청),
// 값 자체(=maxCount 기준)는 여전히 total 항목에서 읽는다.
const totalItem = computed(() => props.items.find((i) => i.key === 'total'))

const maxCount = computed(() => {
  return totalItem.value?.count || Math.max(1, ...props.items.map((i) => i.count))
})

// 사라진 체크포인트 4개(progress/review_done/contract_done/investment_done)는 막대 대신
// 그룹 라벨(값 동반 칩)로 승격한다 — 각 클러스터(=group)가 어느 체크포인트로 이어지는지 매핑.
// wash는 칩 배경에 쓰는 옅은 톤(2026-08-10 오너 요청 — 명칭 색을 옅게 넣는 검토안).
const GROUP_LABEL_BY_GROUP: Record<string, GroupLabel> = {
  plan: { key: 'progress', label: '진행 투자계획', color: 'var(--neutral-line)', wash: 'var(--neutral-soft)' },
  review: { key: 'review_done', label: '심의 완료', color: STAGE.po, wash: 'var(--stage-po-wash)' },
  contract: { key: 'contract_done', label: '계약 완료', color: STAGE.contract, wash: 'var(--stage-contract-wash)' },
  settle: { key: 'investment_done', label: '투자 완료', color: STAGE.execution, wash: 'var(--stage-execution-wash)' },
}

// Drop은 막대로 그리지 않고 좌측 축 영역에 별도 칩으로 표시한다(2026-08-11 오너 요청).
const HIDDEN_BAR_KEYS = new Set(['drop'])
// 이탈(미완료) 항목 판정을 배열의 "마지막 인덱스"가 아니라 key 집합으로 고정한다 — Drop을
// plan 클러스터 배열에서 아예 빼버리면 plan_out이 새 마지막 항목이 되어 기존의 인덱스 기반
// 판정으로는 잘못 회색/이탈 처리되기 때문(2026-08-11 frontend-dev 검토에서 확인된 실제 버그 위험).
const TRAILING_KEYS = new Set(['review_incomplete', 'contract_pending', 'unsettled'])

// 구성요소(component)만 클러스터로 묶는다 — 체크포인트는 더 이상 막대로 그리지 않으므로
// 배열에서 완전히 제외한다(단, props.items 자체는 16개 그대로 유지 — 필터 계약 불변).
// 같은 group이 연속되는 구간이 곧 하나의 클러스터와 정확히 일치한다(plan/review/contract/settle).
// 오너가 요청한 순서(계획→계획외→Drop 등) 그대로 렌더한다 — 원본 데이터 순서를 재배치하지 않는다.
const clusters = computed<Cluster[]>(() => {
  const groups: ProgressFunnelItem[][] = []
  for (const item of props.items) {
    if (item.kind !== 'component') continue
    if (HIDDEN_BAR_KEYS.has(item.key)) continue
    const last = groups[groups.length - 1]
    if (last && last[0].group === item.group) {
      last.push(item)
    } else {
      groups.push([item])
    }
  }

  return groups.map((groupItems) => {
    const items = groupItems.map((item) => ({ item, trailing: TRAILING_KEYS.has(item.key) }))
    return {
      key: groupItems[0].group,
      items,
      hasTrailing: items.some((ci) => ci.trailing),
      groupLabel: GROUP_LABEL_BY_GROUP[groupItems[0].group],
    }
  })
})

function groupLabelCount(key: string): number {
  return props.items.find((i) => i.key === key)?.count ?? 0
}

const dropCount = computed(() => groupLabelCount('drop'))

// 라벨을 공백 기준으로 줄바꿈한다 — 열 너비에 따라 자연 줄바꿈 여부가 갈리면(예: "팀장 심의"는
// 1줄, "센터장 심의"는 2줄) 같은 행 안에서 통일감이 깨진다. 두 단어짜리 라벨은 항상 2줄로
// 고정해 일관되게 보이게 한다(2026-08-10 오너 요청).
function labelLines(label: string): string[] {
  return label.split(' ')
}

// group별 대표색 — 계획=중립, 심의=파랑, 계약=보라, 정산=초록. 이탈/미도달 항목만 회색.
const GROUP_COLORS: Record<ProgressFunnelItem['group'], string> = {
  plan: 'var(--neutral-fill)',
  review: STAGE.po,
  contract: STAGE.contract,
  settle: STAGE.execution,
}
const GRAY = 'var(--trailing-gray)'
// "전체 투자계획"(neutral-fill)보다 살짝 옅은 톤 — 계획/계획외만 이 톤을 쓴다
// (2026-08-07 오너 요청, Drop은 더 이상 막대로 그리지 않는다).
const NEUTRAL_FILL_LIGHT = 'var(--neutral-fill-light)'
const LIGHT_PLAN_KEYS = new Set(['plan', 'plan_out'])

function barColor(item: ProgressFunnelItem, trailing: boolean): string {
  if (trailing) return GRAY
  if (LIGHT_PLAN_KEYS.has(item.key)) return NEUTRAL_FILL_LIGHT
  return GROUP_COLORS[item.group]
}

// 모든 막대의 바닥을 0으로 맞춘다(2026-08-10 오너 요청) — 직전까지의 누적 워터폴 배치를
// 없애고, 각 막대가 자기 값(count/maxCount)만큼만 바닥에서 올라오는 단순 막대로 그린다.
function barHeight(item: ProgressFunnelItem): number {
  return (item.count / maxCount.value) * CHART_HEIGHT
}

function barStyle(ci: ClusterItem): Record<string, string> {
  return {
    bottom: '0px',
    height: `${barHeight(ci.item)}px`,
    background: barColor(ci.item, ci.trailing),
  }
}

// ── 그룹 칩 사이 화살표 위치 계산 ──────────────────────────────────────────
// 클러스터마다 group-spacer(이탈 막대 자리) 유무가 달라 칩 사이 실제 간격이 균일하지
// 않다(진행→심의 간격 ≈20px, 심의→계약·계약→정산 간격 ≈80px). CSS만으로는 각 간격의
// 정중앙을 잡을 수 없어, 렌더된 칩 DOM의 실제 위치를 측정해 화살표를 정확히 그 중간점에
// 절대 배치한다(2026-08-11 프론트엔드 검토).
const plotRef = ref<HTMLElement | null>(null)
const chipRefs = ref<(HTMLElement | null)[]>([])
const arrowPoints = ref<{ left: number; top: number }[]>([])

function setChipRef(el: Element | { $el?: Element } | null, idx: number): void {
  chipRefs.value[idx] = (el as HTMLElement | null) ?? null
}

function measureArrows(): void {
  const plotEl = plotRef.value
  if (!plotEl) return
  const plotRect = plotEl.getBoundingClientRect()
  const points: { left: number; top: number }[] = []

  for (let i = 0; i < chipRefs.value.length - 1; i++) {
    const a = chipRefs.value[i]
    const b = chipRefs.value[i + 1]
    if (!a || !b) continue
    const ar = a.getBoundingClientRect()
    const br = b.getBoundingClientRect()
    points.push({
      left: (ar.right + br.left) / 2 - plotRect.left,
      top: (ar.top + ar.bottom) / 2 - plotRect.top,
    })
  }

  arrowPoints.value = points
}

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  nextTick(measureArrows)
  resizeObserver = new ResizeObserver(() => measureArrows())
  if (plotRef.value) resizeObserver.observe(plotRef.value)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
})

watch(
  () => props.items,
  () => nextTick(measureArrows),
)
</script>

<style scoped>
.funnel {
  overflow-x: auto;
}

.funnel-chart {
  display: flex;
  align-items: flex-start;
  width: 100%;
  min-width: 920px;
  padding: 20px 24px 0 4px;
}

.funnel-axis {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
  height: 230px;
  padding-right: 0.7rem;
  margin-right: 1.4rem;
  border-right: 1px solid var(--border-color);
  flex-shrink: 0;
}

.axis-total {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.1rem;
  cursor: pointer;
  padding: 0.3rem 0.6rem;
  /* Drop 칩(옅은 trailing-gray)보다는 진하되, neutral-fill(--tone-total-border)만큼 어둡지는
     않은 중간 톤(neutral-fill-light)을 배경에 채운다(2026-08-11 오너 재요청 — 검정 글자와
     같이 쓰기엔 neutral-fill이 너무 진했음). */
  border: 1px solid var(--neutral-fill);
  background: var(--neutral-fill-light);
  border-radius: 0.55rem;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.axis-total:hover {
  border-color: var(--neutral-strong);
}

.axis-total.active {
  border-color: var(--neutral-strong);
  box-shadow: inset 0 0 0 1px var(--neutral-strong);
}

/* Drop 칩과 동일한 글씨 양식(크기·굵기·색) — 배경색만 다르고 타이포그래피는 통일한다
   (2026-08-11 오너 요청: "전체 투자계획" 값 글자가 더 굵어 보인다는 피드백). */
.axis-total-label {
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--text-subtle);
  white-space: nowrap;
}

.axis-total-value {
  font-size: 0.82rem;
  font-weight: 800;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

/* Drop 막대를 없애고 이 칩으로 대체한다(2026-08-11 오너 요청) — 이탈 막대와 동일한
   trailing-gray를 그대로 유지해 "회색=이탈/미완료" 색 언어를 지키되, 테두리를 없애고
   값 글자 크기를 전체 투자계획보다 한 단계 작게 둬 부속 정보임을 드러낸다. */
.drop-chip {
  display: flex;
  align-items: baseline;
  gap: 0.3rem;
  cursor: pointer;
  padding: 0.22rem 0.6rem;
  border: 1px solid transparent;
  background: var(--trailing-gray);
  border-radius: 0.5rem;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.drop-chip:hover {
  border-color: var(--text-subtle);
}

.drop-chip.active {
  border-color: var(--text-main);
  box-shadow: inset 0 0 0 1px var(--text-main);
}

.drop-chip .lbl {
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--text-subtle);
  white-space: nowrap;
}

.drop-chip .val {
  font-size: 0.82rem;
  font-weight: 800;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.axis-zero {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--text-subtle);
}

/* 클러스터가 4개뿐이라 컨테이너 폭에 맞춰 사이 간격을 유연하게 벌려서(space-between)
   오른쪽에 여백이 남지 않고 패널 폭을 끝까지 채우도록 한다(2026-08-10 오너 피드백). */
.funnel-plot {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex: 1 1 auto;
  gap: 20px;
}

/* x축 기준선 — 클러스터마다 따로 그리면(.funnel-bars의 border-bottom) 클러스터 사이 간격만큼
   선이 끊겨 보인다(2026-08-10 오너 피드백). 막대 높이(230px)에 맞춰 플롯 전체 폭을 가로지르는
   선 하나를 별도로 올려서 끊김 없이 이어지게 한다. left를 -1.4rem(=.funnel-axis의
   margin-right)만큼 왼쪽으로 늘려 y축 세로선과 정확히 맞닿게 한다 — 그렇지 않으면 축과
   기준선 사이 여백만큼 원점(0) 모서리가 끊겨 보인다(2026-08-10 오너 피드백, 계획 막대 옆
   기준선이 0까지 안 이어지는 문제).*/
.funnel-plot-baseline {
  position: absolute;
  left: -1.4rem;
  right: 0;
  top: 230px;
  border-top: 1px solid var(--border-color);
  pointer-events: none;
}

.funnel-arrows {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.chip-arrow {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  line-height: 0;
}

.funnel-cluster {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex-shrink: 0;
}

.funnel-bars {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 230px;
}

.funnel-bar-col {
  position: relative;
  width: 60px;
  height: 100%;
  cursor: pointer;
  flex-shrink: 0;
}

.funnel-bar-col.wide-label {
  width: 84px;
}

.funnel-bar {
  position: absolute;
  left: 0;
  right: 0;
  border-radius: 0.32rem 0.32rem 0 0;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.funnel-bar.narrow {
  left: 12px;
  right: 12px;
}

.funnel-bar-col:hover .funnel-bar {
  transform: translateY(-3px);
  box-shadow: 0 3px 6px rgba(15, 23, 42, 0.22);
}

.funnel-bar-col.active .funnel-bar {
  transform: translateY(-3px);
  box-shadow: 0 3px 6px rgba(15, 23, 42, 0.22), inset 0 0 0 1.5px var(--text-main);
}

.funnel-bar-value {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.78rem;
  font-weight: 800;
  color: var(--text-main);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.funnel-bar-value.muted {
  color: var(--text-subtle);
  font-weight: 700;
}

.funnel-item-labels {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  /* 라벨 길이에 따라 1~2줄로 다르게 줄바꿈되면 클러스터마다 다음 행(그룹 칩)의 시작
     높이가 어긋난다 — 2줄 기준 높이로 고정해 4개 그룹 칩 행을 항상 나란히 맞춘다
     (2026-08-10 오너 요청). */
  min-height: 2.1rem;
}

.funnel-label {
  width: 60px;
  font-size: 0.8rem;
  color: var(--text-muted);
  font-weight: 650;
  line-height: 1.3;
  text-align: center;
  word-break: keep-all;
  cursor: pointer;
  flex-shrink: 0;
}

.funnel-label.wide-label {
  width: 84px;
}

.label-line {
  display: block;
}

.funnel-label:hover {
  color: var(--text-main);
  text-decoration: underline;
}

.funnel-label.active {
  color: var(--text-main);
  font-weight: 750;
}

.funnel-group-row {
  display: flex;
  gap: 8px;
}

/* 그룹 칩은 진행분(계획/계획외 등) 막대들 아래에만 놓이고, 맨 뒤 이탈(미완료) 막대가 있는
   클러스터만 그 폭만큼 spacer로 비워 칩이 그 아래까지 걸치지 않게 한다. 계획 클러스터는
   Drop 제거로 더 이상 이탈 막대가 없어 spacer 없이 칩이 전체 폭을 그대로 쓴다
   (2026-08-11 오너 요청 — "계획/계획외 아래에 진행 투자계획이 오도록"). */
.group-chip {
  flex: 1 1 auto;
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 0.3rem;
  border: 1px solid transparent;
  border-radius: 0.55rem;
  padding: 0.24rem 0.65rem;
  font-size: 0.8rem;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.group-chip b {
  font-size: inherit;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.group-chip:hover {
  border-color: var(--text-subtle);
}

.group-chip.active {
  border-color: var(--text-main);
  box-shadow: inset 0 0 0 1px var(--text-main);
}

.group-spacer {
  width: 60px;
  flex-shrink: 0;
}
</style>
