<template>
  <div
    class="edit-scrim"
    @click="$emit('cancel')"
  />
  <div
    class="edit-panel"
    role="dialog"
    aria-modal="true"
    :aria-label="mode === 'add' ? '행 추가' : '행 수정'"
  >
    <div class="edit-panel-header">
      <h4>{{ mode === 'add' ? '행 추가' : `행 수정 (NO ${initialValues?.NO ?? ''})` }}</h4>
      <button
        type="button"
        class="edit-close"
        aria-label="닫기"
        @click="$emit('cancel')"
      >
        ×
      </button>
    </div>

    <p class="edit-freeform-notice">
      형식 안내가 없는 항목은 자유 입력입니다.
    </p>

    <div class="edit-panel-body">
      <label
        v-for="col in editableColumns"
        :key="col.key"
        class="edit-field"
        :class="{ 'has-error': errors[col.key] }"
      >
        <span>{{ col.label }}</span>
        <input
          :value="values[col.key]"
          type="text"
          :inputmode="col.type === 'money' ? 'numeric' : 'text'"
          :placeholder="col.placeholder ?? undefined"
          @input="handleFieldInput(col, $event)"
        >
        <span
          v-if="errors[col.key]"
          class="edit-field-error"
        >{{ errors[col.key] }}</span>
      </label>
    </div>

    <div class="edit-panel-footer">
      <button
        type="button"
        class="edit-cancel"
        @click="$emit('cancel')"
      >
        취소
      </button>
      <button
        type="button"
        class="edit-save"
        :disabled="saving || hasErrors"
        @click="handleSave"
      >
        {{ saving ? '저장 중...' : '저장' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import type { AdminRawRow, AdminRowColumn } from '../../types/api'

const props = defineProps<{
  columns: AdminRowColumn[]
  mode: 'add' | 'edit'
  initialValues?: AdminRawRow
  saving: boolean
}>()

const emit = defineEmits<{
  save: [fields: Record<string, string>]
  cancel: []
}>()

// 기성_월/기성_금액, 기성_월_예측/기성_금액_예측 — 슬래시 구분 개수가 서로 일치해야 하는 쌍
// (backend/app/data/columns.py의 PROGRESS_PAIRS와 동일한 규칙을 프론트에서도 즉시 피드백용으로 미러링).
const PROGRESS_PAIRS: [string, string][] = [
  ['기성_월', '기성_금액'],
  ['기성_월_예측', '기성_금액_예측'],
]

// NO는 서버가 채번/식별에 쓰는 값이라 편집 폼에는 노출하지 않는다.
const editableColumns = computed(() => props.columns.filter((col) => col.key !== 'NO'))

const values = reactive<Record<string, string>>(
  Object.fromEntries(editableColumns.value.map((col) => [col.key, props.initialValues?.[col.key] ?? ''])),
)

// 금액 컬럼은 숫자만 입력되도록 가볍게 걸러준다.
function handleFieldInput(col: AdminRowColumn, event: Event): void {
  const raw = (event.target as HTMLInputElement).value
  values[col.key] = col.type === 'money' ? raw.replace(/[^0-9]/g, '') : raw
}

function splitMulti(value: string): string[] {
  return value
    .split(/[/|;]+/)
    .map((token) => token.trim())
    .filter(Boolean)
}

// 백엔드 하이브리드 검증(금액 형식 + 기성 월/금액 개수 일치)을 저장 전에 미리 보여준다.
const errors = computed<Record<string, string>>(() => {
  const errs: Record<string, string> = {}

  for (const col of editableColumns.value) {
    const value = values[col.key]?.trim() ?? ''
    if (col.type === 'money' && value && !/^-?\d+$/.test(value)) {
      errs[col.key] = '숫자만 입력해주세요.'
    }
  }

  for (const [monthKey, amountKey] of PROGRESS_PAIRS) {
    const monthCount = splitMulti(values[monthKey] ?? '').length
    const amountCount = splitMulti(values[amountKey] ?? '').length
    if (monthCount !== amountCount) {
      const msg = `구분 개수가 일치해야 합니다 (${monthCount}개 vs ${amountCount}개).`
      errs[monthKey] = msg
      errs[amountKey] = msg
    }
  }

  return errs
})

const hasErrors = computed(() => Object.keys(errors.value).length > 0)

function handleSave(): void {
  if (hasErrors.value) return

  if (props.mode === 'edit') {
    const changed: Record<string, string> = {}
    for (const col of editableColumns.value) {
      const current = values[col.key]
      const original = props.initialValues?.[col.key] ?? ''
      if (current !== original) changed[col.key] = current
    }

    if (Object.keys(changed).length === 0) {
      emit('cancel')
      return
    }

    emit('save', changed)
    return
  }

  emit('save', { ...values })
}
</script>

<style scoped>
.edit-scrim {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.32);
  z-index: 105;
}

.edit-panel {
  position: fixed;
  top: 0;
  right: 0;
  width: min(630px, 95vw);
  height: 100vh;
  overflow-y: auto;
  background: var(--card-bg);
  box-shadow: -8px 0 30px rgba(15, 23, 42, 0.18);
  padding: 1.2rem 1.3rem 1.5rem;
  z-index: 110;
  box-sizing: border-box;
}

.edit-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.edit-panel-header h4 {
  margin: 0;
  font-size: 1rem;
  color: var(--text-main);
}

.edit-close {
  border: none;
  background: none;
  font-size: 1.4rem;
  line-height: 1;
  color: var(--text-subtle);
  cursor: pointer;
}

.edit-close:hover {
  color: var(--text-main);
}

.edit-freeform-notice {
  font-size: 0.74rem;
  color: var(--text-subtle);
  margin: 0 0 0.8rem;
}

.edit-panel-body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.edit-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.78rem;
  color: var(--text-muted);
}

.edit-field input {
  padding: 0.4rem 0.55rem;
  border: 1px solid var(--border-color);
  border-radius: 0.4rem;
  font-size: 0.82rem;
  box-sizing: border-box;
}

.edit-field.has-error input {
  border-color: var(--tone-bad-border);
}

.edit-field-error {
  font-size: 0.72rem;
  color: var(--tone-bad-border);
}

.edit-panel-footer {
  display: flex;
  gap: 0.5rem;
  margin-top: 1.1rem;
  position: sticky;
  bottom: 0;
  background: var(--card-bg);
  padding-top: 0.6rem;
  border-top: 1px solid var(--border-color);
}

.edit-cancel,
.edit-save {
  flex: 1;
  padding: 0.5rem 0;
  border-radius: 0.5rem;
  font-weight: 700;
  cursor: pointer;
}

.edit-cancel {
  border: 1px solid var(--border-color);
  background: var(--card-bg);
  color: var(--text-main);
}

.edit-save {
  border: none;
  background: var(--select-fill);
  color: var(--select-fill-text);
}

.edit-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
