<template>
  <div
    v-if="authMode === 'sso'"
    class="admin-form"
  >
    <p class="admin-sso-desc">
      회사 계정(SSO)으로 로그인합니다.
    </p>
    <a
      class="admin-submit admin-sso-btn"
      :href="ssoLoginUrl"
    >
      회사 계정으로 로그인
    </a>
  </div>

  <form
    v-else
    class="admin-form"
    @submit.prevent="handleSubmit"
  >
    <label class="admin-field">
      <span>아이디</span>
      <input
        v-model="username"
        type="text"
        autocomplete="username"
      >
    </label>

    <label class="admin-field">
      <span>비밀번호</span>
      <input
        v-model="password"
        type="password"
        autocomplete="current-password"
      >
    </label>

    <p
      v-if="authError"
      class="admin-error"
    >
      {{ authError }}
    </p>

    <button
      type="submit"
      class="admin-submit"
      :disabled="authLoading"
    >
      {{ authLoading ? '로그인 중...' : '로그인' }}
    </button>
  </form>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAdminAuth } from '../../composables/useAdminAuth'
import { useFilters } from '../../composables/useFilters'
import { SSO_LOGIN_URL } from '../../api/client'

const { login, authLoading, authError } = useAdminAuth()
const { meta } = useFilters()

const authMode = computed(() => meta.value?.auth_mode ?? 'local')
const ssoLoginUrl = SSO_LOGIN_URL

const username = ref('admin')
const password = ref('')

async function handleSubmit(): Promise<void> {
  await login(username.value, password.value)
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

.admin-sso-desc {
  font-size: 0.85rem;
  color: var(--text-muted);
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
  text-align: center;
}

.admin-sso-btn {
  display: block;
  text-decoration: none;
}

.admin-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
