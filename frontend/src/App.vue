<template>
  <div class="page">
    <header class="page-header">
      <p class="small-title">
        {{ meta?.team_name ?? 'A-Infra기술팀' }}
      </p>
      <h1 class="big-title">
        {{ meta?.dashboard_title ?? "Investment Management Dashboard '26" }}
      </h1>
      <p
        v-if="meta"
        class="desc"
      >
        투자 계획, 심의, 계약, 완료 현황을 확인합니다.
      </p>
    </header>

    <div class="page-body">
      <SidebarFilters v-model:open="sidebarOpen" />

      <main class="main-content">
        <nav class="tab-bar">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            class="tab-btn"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </nav>

        <DashboardView v-if="activeTab === 'dashboard'" />
        <StatusDetailView v-else />
      </main>
    </div>

    <AdminModal />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useFilters } from './composables/useFilters'
import AdminModal from './components/admin/AdminModal.vue'
import SidebarFilters from './components/layout/SidebarFilters.vue'
import DashboardView from './views/DashboardView.vue'
import StatusDetailView from './views/StatusDetailView.vue'

const { meta, loadMeta } = useFilters()

const tabs = [
  { key: 'dashboard', label: '투자 종합현황' },
  { key: 'status-detail', label: '투자 진행 상세현황' },
] as const

const initialTab = new URLSearchParams(window.location.search).get('tab')
const activeTab = ref<(typeof tabs)[number]['key']>(
  tabs.some((t) => t.key === initialTab) ? (initialTab as (typeof tabs)[number]['key']) : 'dashboard',
)

const sidebarOpen = ref(false)

onMounted(loadMeta)
</script>

<style scoped>
.page {
  max-width: 1660px;
  margin: 0 auto;
  padding: 2rem 2rem 3rem;
}

.page-header {
  margin-bottom: 1rem;
}

.page-body {
  /*
    SidebarFilters는 이제 FAB + fixed 오버레이 드로어 구조라 문서 흐름에 컬럼을
    예약할 필요가 없다. 기존 flex 레이아웃(사이드바 컬럼 + 본문 컬럼)을 단순 블록으로
    정리해 .main-content가 항상 전체 폭을 사용하도록 한다.
  */
  display: block;
}

.main-content {
  min-width: 0;
}

.tab-bar {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 1.2rem;
}

.tab-btn {
  padding: 0.65rem 1.3rem;
  border: none;
  border-radius: 999px;
  background: none;
  font-size: 1rem;
  font-weight: 650;
  color: var(--text-subtle);
  cursor: pointer;
}

.tab-btn.active {
  color: var(--neutral-strong);
  background: var(--neutral-soft);
  font-weight: 750;
}
</style>
