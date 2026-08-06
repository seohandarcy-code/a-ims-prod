<template>
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
          v-for="(row, idx) in rows"
          :key="idx"
        >
          <td
            v-for="col in columns"
            :key="col.key"
          >
            {{ formatCell(row[col.key], col.format) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
export interface RecordColumn {
  key: string
  label: string
  format?: 'eok' | 'pct1' | 'int' | 'raw'
}

defineProps<{ columns: RecordColumn[]; rows: Record<string, unknown>[] }>()

function formatCell(value: unknown, format?: RecordColumn['format']): string {
  if (value === null || value === undefined) return '-'
  const num = Number(value)

  switch (format) {
    case 'eok':
      return Number.isFinite(num) ? `${(num / 100_000_000).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}억` : '-'
    case 'pct1':
      return Number.isFinite(num) ? `${num.toFixed(1)}%` : '-'
    case 'int':
      return Number.isFinite(num) ? num.toLocaleString() : '-'
    default:
      return String(value)
  }
}
</script>

<style scoped>
.table-wrap {
  overflow-x: auto;
}

.simple-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
  white-space: nowrap;
}

.simple-table th {
  background: var(--card-bg);
  color: var(--text-main);
  font-weight: 800;
  text-align: left;
  padding: 0.45rem 0.6rem 0.5rem;
  border-bottom: 2px solid var(--neutral-strong);
}

.simple-table td {
  padding: 0.4rem 0.6rem;
  border-bottom: 1px solid var(--border-color);
}
</style>
