<template>
  <div class="data-panel">
    <div class="data-panel-toolbar">
      <button
        type="button"
        class="toolbar-btn"
        :disabled="columnActionsDisabled"
        @click="openAddPanel"
      >
        + 행 추가
      </button>

      <template v-if="addingColumn">
        <input
          v-model="newColumnName"
          type="text"
          class="column-name-input"
          placeholder="새 컬럼명"
        >
        <select
          v-model="newColumnType"
          class="column-type-select"
        >
          <option value="text">
            텍스트
          </option>
          <option value="money">
            금액
          </option>
          <option value="date">
            날짜
          </option>
        </select>
        <button
          type="button"
          class="toolbar-btn"
          :disabled="!newColumnName.trim()"
          @click="handleAddColumn"
        >
          추가
        </button>
        <button
          type="button"
          class="toolbar-btn"
          @click="cancelAddColumn"
        >
          취소
        </button>
      </template>
      <button
        v-else
        type="button"
        class="toolbar-btn"
        :disabled="columnActionsDisabled"
        @click="startAddColumn"
      >
        + 컬럼 추가
      </button>

      <button
        type="button"
        class="toolbar-btn"
        @click="handleDownload"
      >
        CSV 다운로드
      </button>

      <template v-if="confirmingRestore">
        <span class="confirm-text">직전 상태로 되돌릴까요?</span>
        <button
          type="button"
          class="toolbar-btn danger"
          @click="handleRestore"
        >
          되돌리기
        </button>
        <button
          type="button"
          class="toolbar-btn"
          @click="confirmingRestore = false"
        >
          취소
        </button>
      </template>
      <button
        v-else
        type="button"
        class="toolbar-btn"
        :disabled="!data?.has_backup"
        @click="startRestore"
      >
        되돌리기
      </button>

      <template v-if="pendingDeleteColumnKey">
        <span class="confirm-text">
          '{{ pendingDeleteColumnKey }}' 컬럼을 삭제할까요? (해당 컬럼의 모든 행 값도 함께 삭제됩니다)
        </span>
        <button
          type="button"
          class="toolbar-btn danger"
          @click="handleDeleteColumn(pendingDeleteColumnKey)"
        >
          삭제
        </button>
        <button
          type="button"
          class="toolbar-btn"
          @click="pendingDeleteColumnKey = null"
        >
          취소
        </button>
      </template>
    </div>

    <p
      v-if="error"
      class="admin-error"
    >
      {{ error }}
    </p>
    <p
      v-if="loading"
      class="admin-loading"
    >
      불러오는 중...
    </p>

    <AdminRawTable
      v-else-if="data"
      :columns="data.columns"
      :rows="data.rows"
      :pending-delete-no="pendingDeleteNo"
      :pending-delete-column-key="pendingDeleteColumnKey"
      :column-actions-disabled="columnActionsDisabled"
      @edit="openEditPanel"
      @delete-click="(row) => (pendingDeleteNo = row.NO)"
      @cancel-delete="pendingDeleteNo = null"
      @confirm-delete="handleDelete"
      @delete-column-click="(key) => (pendingDeleteColumnKey = key)"
    />

    <RowEditPanel
      v-if="panelMode"
      :columns="data?.columns ?? []"
      :mode="panelMode"
      :initial-values="editingRow"
      :saving="saving"
      @save="handleSave"
      @cancel="closePanel"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAdminRawData } from '../../composables/useAdminRawData'
import type { AddColumnRequest, AdminRawRow } from '../../types/api'
import AdminRawTable from '../table/AdminRawTable.vue'
import RowEditPanel from './RowEditPanel.vue'

const {
  data,
  loading,
  error,
  load,
  editRow,
  addRow,
  deleteRow,
  restoreBackup,
  addColumn,
  deleteColumn,
  downloadCsv,
} = useAdminRawData()

const panelMode = ref<'add' | 'edit' | null>(null)
const editingRow = ref<AdminRawRow | undefined>(undefined)
const saving = ref(false)

const pendingDeleteNo = ref<string | null>(null)
const confirmingRestore = ref(false)

const addingColumn = ref(false)
const newColumnName = ref('')
const newColumnType = ref<NonNullable<AddColumnRequest['type']>>('text')
const pendingDeleteColumnKey = ref<string | null>(null)

// 행 수정/추가 패널이 열려 있는 동안 컬럼 구성이 바뀌면 폼 상태가 깨질 수 있어
// 컬럼 추가/삭제 조작을 잠근다.
const columnActionsDisabled = computed(() => panelMode.value !== null)

function openAddPanel(): void {
  editingRow.value = undefined
  panelMode.value = 'add'
}

function openEditPanel(row: AdminRawRow): void {
  editingRow.value = row
  panelMode.value = 'edit'
}

function closePanel(): void {
  panelMode.value = null
  editingRow.value = undefined
}

async function handleSave(fields: Record<string, string>): Promise<void> {
  saving.value = true
  const ok =
    panelMode.value === 'add'
      ? await addRow(fields)
      : await editRow(editingRow.value?.NO ?? '', fields)
  saving.value = false
  if (ok) closePanel()
}

async function handleDelete(row: AdminRawRow): Promise<void> {
  await deleteRow(row.NO)
  pendingDeleteNo.value = null
}

function startRestore(): void {
  addingColumn.value = false
  pendingDeleteColumnKey.value = null
  confirmingRestore.value = true
}

async function handleRestore(): Promise<void> {
  await restoreBackup()
  confirmingRestore.value = false
}

function startAddColumn(): void {
  confirmingRestore.value = false
  pendingDeleteColumnKey.value = null
  addingColumn.value = true
}

function cancelAddColumn(): void {
  addingColumn.value = false
  newColumnName.value = ''
  newColumnType.value = 'text'
}

async function handleAddColumn(): Promise<void> {
  const ok = await addColumn(newColumnName.value, newColumnType.value)
  if (ok) cancelAddColumn()
}

async function handleDeleteColumn(key: string): Promise<void> {
  await deleteColumn(key)
  pendingDeleteColumnKey.value = null
}

async function handleDownload(): Promise<void> {
  await downloadCsv()
}

onMounted(load)
</script>

<style scoped>
.data-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.data-panel-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.8rem;
  flex-shrink: 0;
}

.toolbar-btn {
  padding: 0.45rem 0.9rem;
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  background: var(--neutral-soft);
  color: var(--text-main);
  font-size: 0.8rem;
  font-weight: 650;
  cursor: pointer;
}

.toolbar-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.toolbar-btn.danger {
  background: #fff;
  color: var(--tone-bad-border);
  border-color: var(--tone-bad-border);
}

.column-name-input {
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  font-size: 0.8rem;
  box-sizing: border-box;
}

.column-type-select {
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  font-size: 0.8rem;
  background: var(--card-bg);
  color: var(--text-main);
}

.confirm-text {
  font-size: 0.78rem;
  color: var(--tone-bad-border);
}

.admin-error {
  font-size: 0.8rem;
  color: var(--tone-bad-border);
  margin: 0 0 0.6rem;
}

.admin-loading {
  font-size: 0.82rem;
  color: var(--text-muted);
  margin: 0 0 0.6rem;
}
</style>
