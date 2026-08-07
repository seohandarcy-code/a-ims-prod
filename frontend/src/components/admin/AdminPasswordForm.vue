<template>
  <form
    class="admin-form"
    @submit.prevent="handleSubmit"
  >
    <label class="admin-field">
      <span>현재 비밀번호</span>
      <input
        v-model="currentPassword"
        type="password"
        autocomplete="current-password"
      >
    </label>

    <label class="admin-field">
      <span>새 비밀번호</span>
      <input
        v-model="newPassword"
        type="password"
        autocomplete="new-password"
      >
    </label>

    <p
      v-if="authError"
      class="admin-error"
    >
      {{ authError }}
    </p>
    <p
      v-if="success"
      class="admin-success"
    >
      비밀번호가 변경되었습니다. (서버 재기동 시 다시 0000으로 초기화됩니다.)
    </p>

    <button
      type="submit"
      class="admin-submit"
      :disabled="authLoading"
    >
      {{ authLoading ? '변경 중...' : '비밀번호 변경' }}
    </button>
  </form>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAdminAuth } from '../../composables/useAdminAuth'

const { changePassword, authLoading, authError } = useAdminAuth()

const currentPassword = ref('')
const newPassword = ref('')
const success = ref(false)

async function handleSubmit(): Promise<void> {
  success.value = false
  const ok = await changePassword(currentPassword.value, newPassword.value)
  if (ok) {
    success.value = true
    currentPassword.value = ''
    newPassword.value = ''
  }
}
</script>

<style scoped>
.admin-form {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  max-width: 320px;
}

.admin-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.82rem;
  color: var(--text-muted);
}

.admin-field input {
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  font-size: 0.9rem;
  box-sizing: border-box;
}

.admin-error {
  font-size: 0.8rem;
  color: var(--tone-bad-border);
  margin: 0;
}

.admin-success {
  font-size: 0.8rem;
  color: var(--tone-execution-border);
  margin: 0;
}

.admin-submit {
  padding: 0.55rem 0;
  border: none;
  border-radius: 0.5rem;
  background: var(--select-fill);
  color: var(--select-fill-text);
  font-weight: 700;
  cursor: pointer;
}

.admin-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
