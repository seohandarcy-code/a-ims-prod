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
        <thead>
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in filteredRows"
            :key="String(row.no)"
          >
            <td
              v-for="col in columns"
              :key="col.key"
              :class="{ 'cell-left': col.key === 'title' }"
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
import { computed, ref } from 'vue'
import type { DetailColumn } from '../../types/api'

const props = defineProps<{
  columns: DetailColumn[]
  searchKeys: string[]
  rows: Record<string, unknown>[]
}>()

const search = ref('')

const filteredRows = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return props.rows

  return props.rows.filter((row) =>
    props.searchKeys.some((key) => String(row[key] ?? '').toLowerCase().includes(term)),
  )
})

function formatMoney(value: unknown): string {
  const num = Number(value ?? 0)
  return `${num.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}억`
}

function clampPct(value: unknown): number {
  const num = Number(value ?? 0)
  return Math.max(0, Math.min(100, num))
}
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
  border-bottom: 2px solid var(--neutral-strong);
}

.simple-table td {
  padding: 0.4rem 0.6rem;
  border-bottom: 1px solid var(--border-color);
  text-align: center;
}

.simple-table td.cell-left {
  text-align: left;
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
  background: var(--unexecuted-color);
  border-radius: 0.3rem;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--samsung-blue);
}

.empty {
  padding: 1.2rem;
  text-align: center;
  color: var(--text-muted);
}
</style>
