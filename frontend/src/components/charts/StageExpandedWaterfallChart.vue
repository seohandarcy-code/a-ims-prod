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
        <span class="axis-zero">0</span>
      </div>

      <div class="funnel-plot">
        <div class="funnel-plot-baseline" />
        <div
          v-for="cluster in clusters"
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
                {{ ci.trailing && ci.item.count > 0 ? '-' : '' }}{{ ci.item.count.toLocaleString() }}
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
              class="group-chip"
              :class="{ active: selectedKey === cluster.groupLabel.key }"
              :style="{ background: cluster.groupLabel.wash }"
              role="button"
              tabindex="0"
              @click="emit('select', cluster.groupLabel.key)"
              @keydown.enter="emit('select', cluster.groupLabel.key)"
            >
              <span :style="{ color: cluster.groupLabel.color }">{{ cluster.groupLabel.label }}</span>
              <b :style="{ color: cluster.groupLabel.color }">{{ groupLabelCount(cluster.groupLabel.key).toLocaleString() }}</b>
            </span>
            <span class="group-spacer" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
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

// 구성요소(component)만 클러스터로 묶는다 — 체크포인트는 더 이상 막대로 그리지 않으므로
// 배열에서 완전히 제외한다(단, props.items 자체는 16개 그대로 유지 — 필터 계약 불변).
// 같은 group이 연속되는 구간이 곧 하나의 클러스터와 정확히 일치한다(plan/review/contract/settle).
// 오너가 요청한 순서(계획→계획외→Drop 등) 그대로 렌더한다 — 원본 데이터 순서를 재배치하지 않는다.
const clusters = computed<Cluster[]>(() => {
  const groups: ProgressFunnelItem[][] = []
  for (const item of props.items) {
    if (item.kind !== 'component') continue
    const last = groups[groups.length - 1]
    if (last && last[0].group === item.group) {
      last.push(item)
    } else {
      groups.push([item])
    }
  }

  return groups.map((groupItems) => ({
    key: groupItems[0].group,
    items: groupItems.map((item, idx) => ({ item, trailing: idx === groupItems.length - 1 })),
    groupLabel: GROUP_LABEL_BY_GROUP[groupItems[0].group],
  }))
})

function groupLabelCount(key: string): number {
  return props.items.find((i) => i.key === key)?.count ?? 0
}

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
const GRAY = '#DFDEE7'
// "전체 투자계획"(neutral-fill)보다 살짝 옅은 톤 — 계획/계획외만 이 톤을 쓴다
// (2026-08-07 오너 요청, Drop은 neutral-fill 그대로 유지).
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
  justify-content: space-between;
  align-items: flex-end;
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
  border: 1px solid var(--border-color);
  background: var(--neutral-soft);
  border-radius: 0.55rem;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.axis-total:hover {
  border-color: var(--text-subtle);
}

.axis-total.active {
  border-color: var(--text-main);
  box-shadow: inset 0 0 0 1px var(--text-main);
}

.axis-total-label {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--text-subtle);
  white-space: nowrap;
}

.axis-total-value {
  font-size: 1.08rem;
  font-weight: 800;
  color: var(--text-main);
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
   선 하나를 별도로 올려서 끊김 없이 이어지게 한다. */
.funnel-plot-baseline {
  position: absolute;
  left: 0;
  right: 0;
  top: 230px;
  border-top: 1px solid var(--border-color);
  pointer-events: none;
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

/* 그룹 칩은 진행분(계획/계획외 등) 막대들 아래에만 놓이고, 맨 뒤 이탈(Drop/미완료) 막대
   폭만큼은 비워 칩이 그 아래까지 걸치지 않게 한다. */
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
  font-size: 0.92rem;
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
