<template>
  <div class="access-panel">
    <div class="access-panel-toolbar">
      <input
        v-model="newSsoId"
        type="text"
        class="access-input"
        placeholder="사번/아이디(SSO 매칭키)"
      >
      <input
        v-model="newName"
        type="text"
        class="access-input"
        placeholder="이름"
      >
      <input
        v-model="newTeam"
        type="text"
        class="access-input"
        placeholder="팀"
      >
      <label class="access-admin-check">
        <input
          v-model="newIsAdmin"
          type="checkbox"
        >
        관리자
      </label>
      <button
        type="button"
        class="toolbar-btn"
        :disabled="!newSsoId.trim() || !newName.trim() || creating"
        @click="handleCreate"
      >
        + 등록
      </button>
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

    <table
      v-else
      class="access-table"
    >
      <thead>
        <tr>
          <th>사번/아이디</th>
          <th>이름</th>
          <th>팀</th>
          <th>관리자</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="user in users"
          :key="user.sso_id"
        >
          <td>{{ user.sso_id }}</td>
          <td>
            <input
              v-model="editState[user.sso_id].name"
              type="text"
              class="access-input"
            >
          </td>
          <td>
            <input
              v-model="editState[user.sso_id].team"
              type="text"
              class="access-input"
            >
          </td>
          <td>
            <input
              v-model="editState[user.sso_id].is_admin"
              type="checkbox"
            >
          </td>
          <td class="access-row-actions">
            <button
              type="button"
              class="toolbar-btn"
              @click="handleUpdate(user.sso_id)"
            >
              저장
            </button>
            <template v-if="pendingDeleteId === user.sso_id">
              <button
                type="button"
                class="toolbar-btn danger"
                @click="handleDelete(user.sso_id)"
              >
                삭제 확인
              </button>
              <button
                type="button"
                class="toolbar-btn"
                @click="pendingDeleteId = null"
              >
                취소
              </button>
            </template>
            <button
              v-else
              type="button"
              class="toolbar-btn danger"
              @click="pendingDeleteId = user.sso_id"
            >
              삭제
            </button>
          </td>
        </tr>
        <tr v-if="users.length === 0">
          <td
            colspan="5"
            class="access-empty"
          >
            등록된 사용자가 없습니다.
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useAccessUsers } from '../../composables/useAccessUsers'

const { users, loading, error, load, createUser, updateUser, deleteUser } = useAccessUsers()

const newSsoId = ref('')
const newName = ref('')
const newTeam = ref('')
const newIsAdmin = ref(false)
const creating = ref(false)
const pendingDeleteId = ref<string | null>(null)

// 행별 편집 상태 — 목록이 바뀔 때마다 각 사용자 값으로 다시 채운다(다른 곳에서
// 편집 중이 아니라는 전제 — 관리자 1명이 쓰는 화면이라 충돌 걱정 없음).
const editState = reactive<Record<string, { name: string; team: string; is_admin: boolean }>>({})

watch(
  users,
  (list) => {
    for (const key of Object.keys(editState)) delete editState[key]
    for (const user of list) {
      editState[user.sso_id] = { name: user.name, team: user.team, is_admin: user.is_admin }
    }
  },
  { immediate: true },
)

async function handleCreate(): Promise<void> {
  creating.value = true
  const ok = await createUser(newSsoId.value.trim(), newName.value.trim(), newTeam.value.trim(), newIsAdmin.value)
  creating.value = false
  if (ok) {
    newSsoId.value = ''
    newName.value = ''
    newTeam.value = ''
    newIsAdmin.value = false
  }
}

async function handleUpdate(ssoId: string): Promise<void> {
  const edited = editState[ssoId]
  if (!edited) return
  await updateUser(ssoId, edited.name.trim(), edited.team.trim(), edited.is_admin)
}

async function handleDelete(ssoId: string): Promise<void> {
  await deleteUser(ssoId)
  pendingDeleteId.value = null
}

onMounted(load)
</script>

<style scoped>
.access-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.access-panel-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.8rem;
  flex-shrink: 0;
}

.access-admin-check {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.8rem;
  color: var(--text-main);
}

.access-input {
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  font-size: 0.8rem;
  box-sizing: border-box;
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

.access-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.access-table th,
.access-table td {
  padding: 0.5rem 0.6rem;
  border-bottom: 1px solid var(--border-color);
  text-align: left;
}

.access-row-actions {
  display: flex;
  gap: 0.4rem;
}

.access-empty {
  text-align: center;
  color: var(--text-muted);
  padding: 1.2rem;
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
