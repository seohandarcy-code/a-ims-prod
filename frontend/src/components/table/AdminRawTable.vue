<template>
  <div class="raw-table-wrap">
    <input
      v-model="search"
      type="text"
      class="search-input"
      placeholder="전체 컬럼에서 검색"
    >

    <div class="table-frame">
      <div class="table-wrap">
        <table class="simple-table">
          <thead>
            <tr>
              <th class="action-col" />
              <th
                v-for="col in columns"
                :key="col.key"
                class="col-header"
                :class="{ custom: col.deletable, 'pending-delete': pendingDeleteColumnKey === col.key }"
              >
                <span class="col-header-inner">
                  <span class="col-header-label">{{ col.label }}</span>
                  <span
                    v-if="col.deletable"
                    class="custom-badge"
                  >커스텀</span>
                  <button
                    v-if="col.deletable"
                    type="button"
                    class="col-delete-btn"
                    :disabled="columnActionsDisabled"
                    :aria-label="`${col.label} 컬럼 삭제 (커스텀 컬럼)`"
                    :title="`${col.label} 컬럼 삭제`"
                    @click="$emit('delete-column-click', col.key)"
                  >
                    ×
                  </button>
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in filteredRows"
              :key="String(row.NO)"
            >
              <td class="action-col action-cell">
                <template v-if="pendingDeleteNo === row.NO">
                  <span class="confirm-text">삭제할까요?</span>
                  <button
                    type="button"
                    class="row-confirm-btn"
                    @click="$emit('confirm-delete', row)"
                  >
                    삭제
                  </button>
                  <button
                    type="button"
                    class="row-cancel-btn"
                    @click="$emit('cancel-delete')"
                  >
                    취소
                  </button>
                </template>
                <template v-else>
                  <button
                    type="button"
                    class="row-edit-btn"
                    @click="$emit('edit', row)"
                  >
                    수정
                  </button>
                  <button
                    type="button"
                    class="row-delete-btn"
                    @click="$emit('delete-click', row)"
                  >
                    삭제
                  </button>
                </template>
              </td>
              <td
                v-for="col in columns"
                :key="col.key"
              >
                {{ row[col.key] }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AdminRawRow, AdminRowColumn } from '../../types/api'

const props = defineProps<{
  columns: AdminRowColumn[]
  rows: AdminRawRow[]
  pendingDeleteNo: string | null
  pendingDeleteColumnKey: string | null
  columnActionsDisabled: boolean
}>()

defineEmits<{
  edit: [row: AdminRawRow]
  'delete-click': [row: AdminRawRow]
  'confirm-delete': [row: AdminRawRow]
  'cancel-delete': []
  'delete-column-click': [key: string]
}>()

const search = ref('')

const filteredRows = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return props.rows
  return props.rows.filter((row) =>
    Object.values(row).some((v) => String(v ?? '').toLowerCase().includes(term)),
  )
})
</script>

<style scoped>
.raw-table-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.search-input {
  width: 100%;
  padding: 0.45rem 0.7rem;
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  margin-bottom: 0.55rem;
  font-size: 0.82rem;
  box-sizing: border-box;
  flex-shrink: 0;
}

.table-frame {
  flex: 1;
  min-height: 0;
  border: 1px solid var(--border-color);
  border-radius: 0.6rem;
  overflow: hidden;
}

.table-wrap {
  height: 100%;
  overflow: auto;
}

.simple-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.76rem;
  white-space: nowrap;
}

.simple-table th {
  position: sticky;
  top: 0;
  background: var(--card-bg);
  color: var(--text-main);
  font-weight: 800;
  text-align: left;
  padding: 0.4rem 0.55rem 0.45rem;
  border-bottom: 2px solid var(--neutral-strong);
}

.simple-table td {
  padding: 0.35rem 0.55rem;
  border-bottom: 1px solid var(--border-color);
}

.col-header.custom {
  background: var(--neutral-soft);
}

.col-header.pending-delete {
  background: rgba(220, 38, 38, 0.08);
}

.col-header-inner {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.custom-badge {
  font-size: 0.62rem;
  font-weight: 700;
  color: var(--text-muted);
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 0.3rem;
  padding: 0.05rem 0.3rem;
  white-space: nowrap;
}

.col-delete-btn {
  border: none;
  background: none;
  color: var(--tone-bad-border);
  font-size: 0.85rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 0.15rem;
  opacity: 0;
  visibility: hidden;
}

.col-header.custom:hover .col-delete-btn,
.col-delete-btn:focus-visible {
  opacity: 1;
  visibility: visible;
}

.col-delete-btn:disabled {
  cursor: not-allowed;
}

.action-col {
  background: var(--card-bg);
}

.action-cell {
  display: flex;
  gap: 0.3rem;
  align-items: center;
}

.row-edit-btn,
.row-delete-btn,
.row-confirm-btn,
.row-cancel-btn {
  border: 1px solid var(--border-color);
  border-radius: 0.4rem;
  padding: 0.2rem 0.5rem;
  font-size: 0.72rem;
  cursor: pointer;
  white-space: nowrap;
}

.row-edit-btn {
  background: var(--neutral-soft);
  color: var(--text-main);
}

.row-delete-btn,
.row-confirm-btn {
  background: #fff;
  color: var(--tone-bad-border);
  border-color: var(--tone-bad-border);
}

.row-cancel-btn {
  background: var(--card-bg);
  color: var(--text-main);
}

.confirm-text {
  font-size: 0.7rem;
  color: var(--tone-bad-border);
  white-space: nowrap;
}
</style>
