<template>
  <div>
    <input
      v-model="search"
      type="text"
      class="search-input"
      placeholder="검색 예: 조직명, 투자명, WBS코드, 담당자, 계획, 완료, 1월"
    >

    <div class="table-wrap">
      <table class="simple-table">
        <colgroup>
          <col
            v-for="col in columns"
            :key="col.key"
            :style="isMonthNarrowCol(col.key) ? { width: '4.4rem' } : undefined"
          >
        </colgroup>
        <thead>
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
              :ref="(el) => setTheadCell(col.key, el as Element | null)"
              class="is-sortable"
              :class="{ 'col-frozen': isFrozenCol(col.key), 'col-frozen-edge': col.key === FROZEN_EDGE_KEY }"
              :style="isFrozenCol(col.key) ? { left: `${leftOffsets[col.key] ?? 0}px` } : undefined"
              @click="onHeaderClick(col)"
            >
              <span class="th-label">{{ col.label }}</span>
              <span
                v-if="sortKey === col.key"
                class="sort-indicator"
              >{{ sortDir === 'asc' ? '▲' : '▼' }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in sortedRows"
            :key="String(row.no)"
            :class="{ 'row-dropped': isDroppedRow(row) }"
          >
            <td
              v-for="col in columns"
              :key="col.key"
              :class="{
                'cell-left': col.key === 'title',
                'col-frozen': isFrozenCol(col.key),
                'col-frozen-edge': col.key === FROZEN_EDGE_KEY,
              }"
              :style="isFrozenCol(col.key) ? { left: `${leftOffsets[col.key] ?? 0}px` } : undefined"
            >
              <template v-if="col.type === 'money'">
                {{ formatMoney(row[col.key]) }}
              </template>
              <template v-else-if="col.type === 'progress'">
                <div class="progress-cell">
                  <div class="progress-track">
                    <div
                      class="progress-fill"
                      :style="{ width: `${clampPct(row[col.key])}%` }"
                    />
                  </div>
                  <span>{{ clampPct(row[col.key]).toFixed(1) }}%</span>
                </div>
              </template>
              <template v-else>
                {{ row[col.key] }}
              </template>
            </td>
          </tr>
        </tbody>
      </table>
      <div
        v-if="!filteredRows.length"
        class="empty"
      >
        검색 결과가 없습니다.
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { DetailColumn } from '../../types/api'

const props = defineProps<{
  columns: DetailColumn[]
  searchKeys: string[]
  rows: Record<string, unknown>[]
}>()

// Drop/타팀이관 행은 동일하게 회색으로 표시한다(2026-09-22 타팀이관 추가).
const DROPPED_PLAN_TYPES = new Set(['Drop', '타팀이관'])
function isDroppedRow(row: Record<string, unknown>): boolean {
  return DROPPED_PLAN_TYPES.has(String(row.plan_type ?? ''))
}

const search = ref('')

const filteredRows = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return props.rows

  return props.rows.filter((row) =>
    props.searchKeys.some((key) => String(row[key] ?? '').toLowerCase().includes(term)),
  )
})

// 항목명(헤더) 클릭 시 오름차순/내림차순 정렬. 같은 컬럼을 다시 누르면 방향만 뒤집는다.
const sortKey = ref<string | null>(null)
const sortDir = ref<'asc' | 'desc'>('asc')

function onHeaderClick(col: DetailColumn): void {
  if (sortKey.value === col.key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = col.key
    sortDir.value = 'asc'
  }
}

function compareValues(a: unknown, b: unknown, type: DetailColumn['type']): number {
  if (type === 'text') {
    return String(a ?? '').localeCompare(String(b ?? ''), 'ko')
  }
  return Number(a ?? 0) - Number(b ?? 0)
}

const sortedRows = computed(() => {
  if (!sortKey.value) return filteredRows.value

  const key = sortKey.value
  const col = props.columns.find((c) => c.key === key)
  const type = col?.type ?? 'text'
  const dir = sortDir.value === 'asc' ? 1 : -1

  return [...filteredRows.value].sort((a, b) => compareValues(a[key], b[key], type) * dir)
})

function formatMoney(value: unknown): string {
  const num = Number(value ?? 0)
  return `${num.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}억`
}

function clampPct(value: unknown): number {
  const num = Number(value ?? 0)
  return Math.max(0, Math.min(100, num))
}

// "계약월"(contract_month_input)이 옆 "심의월"(review_month)보다 눈에 띄게 넓게 렌더링되는
// 문제(2026-08-11 오너 피드백) — table-layout:auto + width:100%에서는 값 길이가 같아도
// 컬럼별로 여백이 고르게 배분되지 않는다. 두 컬럼에 동일한 고정 폭을 줘서 값 길이("N월")에
// 맞는 폭으로 나란히 맞춘다.
const MONTH_NARROW_COLS = new Set(['review_month', 'contract_month_input'])

function isMonthNarrowCol(key: string): boolean {
  return MONTH_NARROW_COLS.has(key)
}

// 가로 스크롤 시 "투자명"까지 왼쪽 컬럼을 고정한다(2026-08-18 오너 요청) — 오른쪽으로
// 스크롤해도 어떤 행인지 계속 확인할 수 있게. table-layout:auto라 컬럼 폭이 내용에 따라
// 달라지므로, 픽셀 폭을 하드코딩하지 않고 실제 렌더링된 헤더 셀 폭을 측정해 누적 left
// 오프셋을 계산한다.
const FROZEN_KEYS = ['no', 'org', 'part', 'owner', 'wbs', 'title']
const FROZEN_EDGE_KEY = 'title'

function isFrozenCol(key: string): boolean {
  return FROZEN_KEYS.includes(key)
}

const theadCells: Record<string, HTMLElement> = {}

function setTheadCell(key: string, el: Element | null): void {
  if (el) theadCells[key] = el as HTMLElement
}

const leftOffsets = ref<Record<string, number>>({})

function recomputeFrozenOffsets(): void {
  let acc = 0
  const offsets: Record<string, number> = {}

  for (const key of FROZEN_KEYS) {
    offsets[key] = acc
    const el = theadCells[key]
    acc += el ? el.offsetWidth : 0
  }

  leftOffsets.value = offsets
}

onMounted(() => {
  nextTick(recomputeFrozenOffsets)
  window.addEventListener('resize', recomputeFrozenOffsets)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', recomputeFrozenOffsets)
})

watch(
  () => props.columns,
  () => nextTick(recomputeFrozenOffsets),
)

// 검색/정렬로 표시되는 값이 바뀌면 table-layout:auto 특성상 컬럼 폭이 미세하게
// 달라질 수 있어 오프셋을 다시 잰다.
watch(sortedRows, () => nextTick(recomputeFrozenOffsets))
</script>

<style scoped>
.search-input {
  width: 100%;
  padding: 0.55rem 0.8rem;
  border: 1px solid var(--border-color);
  border-radius: 0.6rem;
  margin-bottom: 0.6rem;
  font-size: 0.85rem;
  box-sizing: border-box;
}

.table-wrap {
  max-height: 640px;
  overflow: auto;
}

.simple-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.78rem;
  white-space: nowrap;
}

.simple-table th {
  position: sticky;
  top: 0;
  background: var(--card-bg);
  color: var(--text-main);
  font-weight: 800;
  text-align: center;
  padding: 0.45rem 0.6rem 0.5rem;
  border-bottom: 2px solid var(--neutral-fill);
  z-index: 1;
}

.simple-table th.is-sortable {
  cursor: pointer;
  user-select: none;
}

.simple-table th.is-sortable:hover {
  background: var(--neutral-fill);
}

.sort-indicator {
  margin-left: 0.25rem;
  font-size: 0.65rem;
  color: var(--text-muted);
}

.simple-table td {
  padding: 0.4rem 0.6rem;
  border-bottom: 1px solid var(--border-color);
  text-align: center;
}

.simple-table td.cell-left {
  text-align: left;
}

/* 가로 스크롤 시 "투자명"까지 왼쪽 컬럼 고정 */
.simple-table .col-frozen {
  position: sticky;
  background: var(--card-bg);
  z-index: 2;
}

.simple-table th.col-frozen {
  z-index: 3;
}

.simple-table .col-frozen-edge {
  box-shadow: 2px 0 4px rgba(15, 23, 42, 0.08);
}

.row-dropped td {
  color: var(--text-muted);
}

.progress-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  min-width: 120px;
}

.progress-track {
  flex: 1;
  height: 0.5rem;
  background: var(--stage-execution-wash);
  border-radius: 0.3rem;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--stage-execution-ink);
}

.empty {
  padding: 1.2rem;
  text-align: center;
  color: var(--text-muted);
}
</style>
