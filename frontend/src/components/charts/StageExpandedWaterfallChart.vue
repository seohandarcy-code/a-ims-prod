<template>
  <div class="funnel">
    <div class="funnel-chart">
      <div
        v-for="cp in checkpoints"
        :key="`guide-${cp.key}`"
        class="funnel-guide"
        :style="{ bottom: (cp.count / maxCount) * CHART_HEIGHT + 'px' }"
      >
        <span class="funnel-guide-label">{{ cp.count.toLocaleString() }} {{ CHECKPOINT_SHORT_LABEL[cp.key] ?? cp.label }}</span>
      </div>
      <template
        v-for="(slot, slotIdx) in slots"
        :key="slotIdx"
      >
        <div
          class="funnel-slot"
          :class="slot.kind"
          :style="{ marginLeft: slotExtraGap[slotIdx] + 'px' }"
        >
          <div
            v-for="(item, itemIdx) in slot.items"
            :key="item.key"
            class="funnel-bar-col"
            :class="{ wide: slot.kind === 'checkpoint', 'wide-label': item.key === 'irb_path', active: selectedKey === item.key }"
            :style="{ order: isTrailing(itemIdx, slot) ? -1 : 0 }"
            role="button"
            tabindex="0"
            @click="emit('select', item.key)"
            @keydown.enter="emit('select', item.key)"
          >
            <div
              class="funnel-bar"
              :class="{ narrow: item.key === 'irb_path' }"
              :style="barStyle(slot, itemIdx)"
            />
            <div
              class="funnel-bar-value"
              :class="{ muted: isTrailing(itemIdx, slot) }"
              :style="{ bottom: barTop(slot, itemIdx) + 6 + 'px' }"
            >
              {{ isTrailing(itemIdx, slot) && item.count > 0 ? '-' : '' }}{{ item.count.toLocaleString() }}
            </div>
          </div>
        </div>
      </template>
    </div>

    <div class="funnel-labels">
      <template
        v-for="(slot, slotIdx) in slots"
        :key="`label-${slotIdx}`"
      >
        <div
          class="funnel-label-slot"
          :class="slot.kind"
          :style="{ marginLeft: slotExtraGap[slotIdx] + 'px' }"
        >
          <div
            v-for="(item, itemIdx) in slot.items"
            :key="`${item.key}-label`"
            class="funnel-label"
            :class="{ 'wide-label': item.key === 'irb_path', active: selectedKey === item.key }"
            :style="{ order: isTrailing(itemIdx, slot) ? -1 : 0 }"
            role="button"
            tabindex="0"
            @click="emit('select', item.key)"
            @keydown.enter="emit('select', item.key)"
          >
            {{ item.label }}
          </div>
        </div>
      </template>
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

interface Slot {
  kind: 'checkpoint' | 'cluster'
  items: ProgressFunnelItem[]
}

// 연속된 component 항목은 하나의 클러스터로 묶고, checkpoint는 단독 슬롯으로 둔다.
const slots = computed<Slot[]>(() => {
  const result: Slot[] = []
  for (const item of props.items) {
    if (item.kind === 'checkpoint') {
      result.push({ kind: 'checkpoint', items: [item] })
      continue
    }
    const last = result[result.length - 1]
    if (last && last.kind === 'cluster') {
      last.items.push(item)
    } else {
      result.push({ kind: 'cluster', items: [item] })
    }
  }
  return result
})

const maxCount = computed(() => {
  const total = props.items.find((i) => i.key === 'total')
  return total?.count || Math.max(1, ...props.items.map((i) => i.count))
})

// 체크포인트 기준선(점선)용 — 클러스터 막대 사이에서도 34/31/22/10/3 기준을 계속 확인할 수 있게 한다.
const checkpoints = computed(() => props.items.filter((i) => i.kind === 'checkpoint'))

const CHECKPOINT_SHORT_LABEL: Record<string, string> = {
  total: '전체',
  progress: '진행',
  review_done: '심의',
  contract_done: '계약',
  investment_done: '투자',
}

// 체크포인트 "다음"(=그 뒤에 오는 클러스터 앞)에 여백을 등차적으로 넓혀(10/18/26/34px),
// 여유 공간이 오른쪽 끝에 한꺼번에 몰리는 대신 체크포인트마다 자연스럽게 나눠 배치되도록 한다.
// 클러스터는 항상 체크포인트 바로 뒤에 오므로, 클러스터 등장 순서(0~3)에 따라 여백을 부여한다.
const CHECKPOINT_GAP_BASE = 10
const CHECKPOINT_GAP_STEP = 8

const slotExtraGap = computed<number[]>(() => {
  let clusterOrdinal = 0
  return slots.value.map((slot) => {
    if (slot.kind !== 'cluster') return 0
    const gap = CHECKPOINT_GAP_BASE + clusterOrdinal * CHECKPOINT_GAP_STEP
    clusterOrdinal += 1
    return gap
  })
})

// group별 대표색 — 계획=중립, 심의=파랑, 계약=보라, 정산=초록. 이탈/미도달 항목만 회색.
const GROUP_COLORS: Record<ProgressFunnelItem['group'], string> = {
  plan: 'var(--neutral-fill)',
  review: STAGE.po,
  contract: STAGE.contract,
  settle: STAGE.execution,
}
const GRAY = '#DFDEE7'
// "전체 투자계획"(neutral-fill)보다 살짝 옅은 톤 — 계획/계획외/진행 투자계획만 이 톤을 쓴다
// (2026-08-07 오너 요청, Drop·전체 투자계획은 neutral-fill 그대로 유지).
const NEUTRAL_FILL_LIGHT = 'var(--neutral-fill-light)'
const LIGHT_PLAN_KEYS = new Set(['plan', 'plan_out', 'progress'])

function isTrailing(itemIdx: number, slot: Slot): boolean {
  // 클러스터의 마지막 항목 = 다음 체크포인트로 이어지지 않는 탈락분이므로 항상 회색 처리.
  return slot.kind === 'cluster' && itemIdx === slot.items.length - 1
}

function barColor(item: ProgressFunnelItem, itemIdx: number, slot: Slot): string {
  if (isTrailing(itemIdx, slot)) return GRAY
  if (LIGHT_PLAN_KEYS.has(item.key)) return NEUTRAL_FILL_LIGHT
  return GROUP_COLORS[item.group]
}

function barTop(slot: Slot, itemIdx: number): number {
  if (slot.kind === 'checkpoint') {
    return (slot.items[0].count / maxCount.value) * CHART_HEIGHT
  }
  // 탈락(회색) 항목도 배열상 항상 클러스터 마지막이라, 누적 계산을 그대로 쓰면
  // 자연히 이전 체크포인트 값에 맞닿아 위쪽에 떠 있는 형태가 된다(컬럼 위치만 CSS order로 앞당김).
  const before = slot.items.slice(0, itemIdx).reduce((sum, i) => sum + i.count, 0)
  const cumulative = before + slot.items[itemIdx].count
  return (cumulative / maxCount.value) * CHART_HEIGHT
}

function barBottom(slot: Slot, itemIdx: number): number {
  if (slot.kind === 'checkpoint') return 0
  const before = slot.items.slice(0, itemIdx).reduce((sum, i) => sum + i.count, 0)
  return (before / maxCount.value) * CHART_HEIGHT
}

function barStyle(slot: Slot, itemIdx: number): Record<string, string> {
  const item = slot.items[itemIdx]
  const bottom = barBottom(slot, itemIdx)
  const height = (item.count / maxCount.value) * CHART_HEIGHT
  return {
    bottom: `${bottom}px`,
    height: `${height}px`,
    background: barColor(item, itemIdx, slot),
  }
}
</script>

<style scoped>
.funnel {
  overflow-x: auto;
}

.funnel-chart {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: 0.6rem;
  height: 280px;
  min-width: 1060px;
  padding: 44px 85px 0 32px;
  border-bottom: 1px solid var(--border-color);
}

.funnel-guide {
  position: absolute;
  left: 0;
  right: 0;
  height: 0;
  border-top: 1px dashed var(--border-color);
}

.funnel-guide-label {
  position: absolute;
  right: 0.3rem;
  top: -14px;
  font-size: 0.66rem;
  font-weight: 750;
  color: var(--text-muted);
  background: var(--card-bg);
  padding: 0 0.3rem;
  white-space: nowrap;
}

.funnel-slot {
  position: relative;
  height: 230px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  flex: 1 1 auto;
}

.funnel-slot.cluster {
  gap: 8px;
  padding: 0 6px;
  border-radius: 0.5rem 0.5rem 0 0;
  background: rgba(148, 163, 184, 0.08);
}

.funnel-bar-col {
  position: relative;
  width: 31px;
  height: 100%;
  cursor: pointer;
}

.funnel-bar-col.wide {
  width: 62px;
}

.funnel-bar-col.wide-label {
  width: 66px;
}

.funnel-bar {
  position: absolute;
  left: 0;
  right: 0;
  border-radius: 0.28rem 0.28rem 0 0;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.funnel-bar.narrow {
  left: 17.5px;
  right: 17.5px;
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
  font-size: 0.68rem;
  font-weight: 800;
  color: var(--text-main);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.funnel-bar-value.muted {
  color: var(--text-subtle);
  font-weight: 700;
}

.funnel-labels {
  display: flex;
  gap: 0.6rem;
  min-width: 1060px;
  padding: 0.6rem 85px 0 32px;
}

.funnel-label-slot {
  display: flex;
  justify-content: center;
  gap: 8px;
  flex: 1 1 auto;
}

.funnel-label-slot.checkpoint {
  width: 62px;
}

.funnel-label-slot.cluster {
  padding: 0 6px;
}

.funnel-label {
  width: 31px;
  font-size: 0.74rem;
  color: var(--text-muted);
  font-weight: 600;
  line-height: 1.3;
  text-align: center;
  word-break: keep-all;
  cursor: pointer;
}

.funnel-label:hover {
  color: var(--text-main);
  text-decoration: underline;
}

.funnel-label.wide-label {
  width: 66px;
}

.funnel-label.active {
  color: var(--text-main);
  font-weight: 750;
}

.funnel-label-slot.checkpoint .funnel-label {
  width: 62px;
  font-size: 0.82rem;
  font-weight: 750;
  color: var(--text-main);
}
</style>
