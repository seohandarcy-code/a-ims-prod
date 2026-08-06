<template>
  <Teleport to="body">
    <div
      v-if="modalOpen"
      class="admin-scrim"
      @click="close"
    />

    <div
      v-if="modalOpen"
      ref="dialogRef"
      class="admin-dialog"
      :class="{ fullscreen: isFullscreen }"
      role="dialog"
      aria-modal="true"
      aria-label="관리자 설정"
    >
      <div class="admin-dialog-header">
        <h3 class="admin-dialog-title">
          관리자 설정
        </h3>
        <div class="admin-header-actions">
          <button
            type="button"
            class="admin-fullscreen-btn"
            :aria-label="isFullscreen ? '창 모드로 보기' : '전체화면으로 보기'"
            @click="isFullscreen = !isFullscreen"
          >
            {{ isFullscreen ? '⤡' : '⛶' }}
          </button>
          <button
            type="button"
            class="admin-close"
            aria-label="닫기"
            @click="close"
          >
            ×
          </button>
        </div>
      </div>

      <div
        v-if="!isAuthed"
        class="admin-login-stage"
      >
        <AdminLoginForm />
      </div>

      <template v-else>
        <div class="admin-tab-bar">
          <div class="admin-tab-group">
            <button
              type="button"
              class="admin-tab"
              :class="{ active: activeTab === 'data' }"
              @click="activeTab = 'data'"
            >
              전체 데이터
            </button>
            <button
              type="button"
              class="admin-tab"
              :class="{ active: activeTab === 'password' }"
              @click="activeTab = 'password'"
            >
              비밀번호 변경
            </button>
          </div>

          <button
            type="button"
            class="admin-logout-btn"
            @click="logout"
          >
            로그아웃
          </button>
        </div>

        <AdminDataPanel v-if="activeTab === 'data'" />
        <AdminPasswordForm v-else />
      </template>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAdminAuth } from '../../composables/useAdminAuth'
import AdminDataPanel from './AdminDataPanel.vue'
import AdminLoginForm from './AdminLoginForm.vue'
import AdminPasswordForm from './AdminPasswordForm.vue'

const { modalOpen, isAuthed, logout } = useAdminAuth()

const activeTab = ref<'data' | 'password'>('data')
const dialogRef = ref<HTMLDivElement | null>(null)
const isFullscreen = ref(false)

function close(): void {
  modalOpen.value = false
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && modalOpen.value) close()
}

// 열릴 때 다이얼로그 내부 첫 포커스 가능 요소로 이동한다(SidebarFilters 드로어와 동일한 최소 focus 처리).
watch(modalOpen, async (isOpen) => {
  if (!isOpen) {
    activeTab.value = 'data'
    isFullscreen.value = false
    return
  }
  await nextTick()
  const firstFocusable = dialogRef.value?.querySelector<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
  )
  firstFocusable?.focus()
})

onMounted(() => window.addEventListener('keydown', handleKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', handleKeydown))
</script>

<style scoped>
.admin-scrim {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  z-index: 95;
}

.admin-dialog {
  position: fixed;
  inset: 0;
  margin: auto;
  width: min(1380px, 96vw);
  height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
  background: var(--card-bg);
  border-radius: 1rem;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.24);
  padding: 1.4rem 1.6rem 1.6rem;
  z-index: 100;
}

.admin-dialog.fullscreen {
  margin: 0;
  width: 100vw;
  height: 100vh;
  border-radius: 0;
}

.admin-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.8rem;
  flex-shrink: 0;
}

.admin-dialog-title {
  font-size: 1.15rem;
  font-weight: 750;
  color: var(--text-main);
  margin: 0;
}

.admin-login-stage {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.admin-header-actions {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.admin-fullscreen-btn {
  border: none;
  background: none;
  font-size: 1.15rem;
  line-height: 1;
  color: var(--text-subtle);
  cursor: pointer;
  padding: 0.2rem 0.4rem;
}

.admin-fullscreen-btn:hover {
  color: var(--text-main);
}

.admin-close {
  border: none;
  background: none;
  font-size: 1.5rem;
  line-height: 1;
  color: var(--text-subtle);
  cursor: pointer;
  padding: 0.2rem 0.4rem;
}

.admin-close:hover {
  color: var(--text-main);
}

.admin-tab-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 1rem;
  flex-shrink: 0;
}

.admin-tab-group {
  display: flex;
  gap: 0.4rem;
}

.admin-logout-btn {
  border: none;
  background: none;
  padding: 0.4rem 0.2rem;
  font-size: 0.78rem;
  color: var(--text-subtle);
  cursor: pointer;
}

.admin-logout-btn:hover {
  color: var(--text-main);
}

.admin-tab {
  border: none;
  background: none;
  padding: 0.5rem 0.9rem;
  font-size: 0.85rem;
  font-weight: 650;
  color: var(--text-subtle);
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.admin-tab.active {
  color: var(--text-main);
  border-bottom-color: var(--neutral-strong);
}
</style>
