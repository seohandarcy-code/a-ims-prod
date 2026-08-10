<template>
  <button
    ref="fabRef"
    type="button"
    class="filter-fab"
    :class="{ active: open }"
    aria-label="필터 열기"
    :aria-expanded="open"
    aria-controls="filter-drawer-panel"
    @click="toggleDrawer"
  >
    <svg
      viewBox="0 0 24 24"
      width="22"
      height="22"
      fill="none"
      stroke="currentColor"
      stroke-width="1.75"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <line
        x1="4"
        y1="6"
        x2="20"
        y2="6"
      />
      <circle
        cx="9"
        cy="6"
        r="2"
      />
      <line
        x1="4"
        y1="12"
        x2="20"
        y2="12"
      />
      <circle
        cx="15"
        cy="12"
        r="2"
      />
      <line
        x1="4"
        y1="18"
        x2="20"
        y2="18"
      />
      <circle
        cx="9"
        cy="18"
        r="2"
      />
    </svg>
    <span
      v-if="activeGroupCount > 0"
      class="filter-badge"
    >{{ activeGroupCount }}</span>
  </button>

  <Teleport to="body">
    <div
      v-if="open"
      class="filter-scrim"
      @click="closeDrawer"
    />

    <div
      id="filter-drawer-panel"
      ref="drawerRef"
      class="filter-drawer"
      :class="{ open }"
      role="dialog"
      aria-modal="true"
      aria-label="공통 필터"
    >
      <div class="drawer-header">
        <h3 class="sidebar-title">
          공통 필터
        </h3>
        <button
          type="button"
          class="drawer-close"
          aria-label="필터 닫기"
          @click="closeDrawer"
        >
          ×
        </button>
      </div>

      <div class="sidebar-body">
        <div class="filter-group">
          <div class="filter-group-label">
            조직
          </div>

          <div class="filter-controls">
            <button
              type="button"
              class="mini-btn"
              @click="selectAllOrg"
            >
              전체
            </button>
            <button
              type="button"
              class="mini-btn"
              @click="clearAllOrg"
            >
              해제
            </button>
          </div>

          <OrgTree
            mode="multi"
            collapsible
            :nodes="meta?.org_tree ?? []"
          />

          <div class="selected-count">
            선택 {{ orgLeaf.length }}/{{ totalPartCount }}
          </div>
        </div>

        <div class="filter-group">
          <div class="filter-group-label">
            투자 진행 흐름 구분
          </div>

          <div class="filter-controls">
            <button
              type="button"
              class="mini-btn"
              @click="selectAllFlowStage"
            >
              전체
            </button>
            <button
              type="button"
              class="mini-btn"
              @click="clearAllFlowStage"
            >
              해제
            </button>
          </div>

          <div class="option-list">
            <button
              v-for="option in meta?.flow_stage_options ?? []"
              :key="option.key"
              type="button"
              class="option-btn"
              :class="{ active: selectedFlowStage.includes(option.key) }"
              @click="toggleFlowStage(option.key)"
            >
              {{ option.label }}
            </button>
          </div>

          <div class="selected-count">
            선택 {{ selectedFlowStage.length }}/{{ meta?.flow_stage_options.length ?? 0 }}
          </div>
        </div>

        <div
          v-for="group in groups"
          :key="group.key"
          class="filter-group"
        >
          <div class="filter-group-label">
            {{ group.label }}
          </div>

          <div class="filter-controls">
            <button
              type="button"
              class="mini-btn"
              @click="selectAll(group.key)"
            >
              전체
            </button>
            <button
              type="button"
              class="mini-btn"
              @click="clearAll(group.key)"
            >
              해제
            </button>
          </div>

          <div class="option-list">
            <button
              v-for="option in options(group.key)"
              :key="option"
              type="button"
              class="option-btn"
              :class="{ active: selected[group.key].includes(option) }"
              @click="toggleOption(group.key, option)"
            >
              {{ option }}
            </button>
          </div>

          <div class="selected-count">
            선택 {{ selected[group.key].length }}/{{ options(group.key).length }}
          </div>
        </div>
      </div>

      <div class="drawer-footer">
        <button
          type="button"
          class="admin-entry-btn"
          @click="openAdminSettings"
        >
          관리자 설정
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAdminAuth } from '../../composables/useAdminAuth'
import { useFilters, type FilterKey } from '../../composables/useFilters'
import OrgTree from './OrgTree.vue'

const open = defineModel<boolean>('open', { default: false })

const {
  meta,
  selected,
  orgLeaf,
  selectedFlowStage,
  toggleOption,
  selectAll,
  clearAll,
  toggleFlowStage,
  selectAllFlowStage,
  clearAllFlowStage,
  selectAllOrg,
  clearAllOrg,
} = useFilters()
const { modalOpen: adminModalOpen } = useAdminAuth()

const fabRef = ref<HTMLButtonElement | null>(null)
const drawerRef = ref<HTMLDivElement | null>(null)

const groups: { key: FilterKey; label: string }[] = [
  { key: 'leader_opinion', label: '팀장심의 의견' },
  { key: 'center_need', label: '센터장 심의필요' },
]

function options(key: FilterKey): string[] {
  return meta.value?.filter_options[key] ?? []
}

const totalPartCount = computed(() => meta.value?.filter_options.part.length ?? 0)
const totalFlowStageCount = computed(() => meta.value?.flow_stage_options.length ?? 0)

// 활성 필터 배지: 옵션 단위가 아닌 "전체 선택이 아닌 그룹" 개수를 기준으로 한다(오너 확정 사항).
// 조직(팀/PJT/파트) 트리와 "투자 진행 흐름 구분"은 별도 그룹으로 취급해 같은 방식(전체선택 여부)으로 카운트한다.
const activeGroupCount = computed(() => {
  const flatActive = groups.filter((group) => {
    const total = options(group.key).length
    const chosenCount = selected[group.key]?.length ?? 0
    return chosenCount !== total
  }).length

  const orgActive = orgLeaf.length !== totalPartCount.value ? 1 : 0
  const flowStageActive = selectedFlowStage.length !== totalFlowStageCount.value ? 1 : 0

  return flatActive + orgActive + flowStageActive
})

function toggleDrawer(): void {
  open.value = !open.value
}

function closeDrawer(): void {
  if (open.value) open.value = false
}

// 지금은 항상 노출한다. 추후 SSO 연동 시 관리자 권한 여부에 따라
// 이 버튼 자체를 v-if로 감싸는 식으로 조건부 노출로 바꾸면 된다.
function openAdminSettings(): void {
  closeDrawer()
  adminModalOpen.value = true
}

function handleDocumentClick(event: MouseEvent): void {
  if (!open.value) return
  const target = event.target as Node
  if (drawerRef.value?.contains(target)) return
  if (fabRef.value?.contains(target)) return
  closeDrawer()
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && open.value) {
    closeDrawer()
  }
}

// 최소 focus-trap: 열릴 때 드로어 내부 첫 포커스 가능 요소로 이동하고,
// 닫힐 때 트리거(FAB)로 포커스를 되돌린다. 완전한 Tab 순환 가두기는 구현하지 않는다.
watch(open, async (isOpen) => {
  if (isOpen) {
    await nextTick()
    const firstFocusable = drawerRef.value?.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    )
    firstFocusable?.focus()
  } else {
    fabRef.value?.focus()
  }
})

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.filter-fab {
  position: fixed;
  top: 1.5rem;
  left: max(1rem, calc((100vw - 1660px) / 2 - 3.25rem));
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.1);
  color: var(--text-main);
  cursor: pointer;
  padding: 0;
  z-index: 40;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease,
    background 0.15s ease,
    color 0.15s ease,
    border-color 0.15s ease;
}

.filter-fab:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.16);
}

.filter-fab.active {
  background: var(--neutral-soft);
  color: var(--neutral-strong);
  border-color: transparent;
}

@media (prefers-reduced-motion: reduce) {
  .filter-fab {
    transition: none;
  }
}

.filter-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  padding: 0 3px;
  border-radius: 999px;
  background: var(--org-select-fill);
  color: var(--org-select-fill-text);
  font-size: 0.65rem;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
}

.filter-scrim {
  position: fixed;
  inset: 0;
  background: transparent;
  pointer-events: none;
  z-index: 45;
}

@media (max-width: 760px) {
  .filter-scrim {
    background: rgba(15, 23, 42, 0.28);
    pointer-events: auto;
  }
}

.filter-drawer {
  position: fixed;
  top: 0;
  left: 0;
  width: 264px;
  height: 100vh;
  overflow-y: auto;
  background: var(--card-bg);
  border-radius: 0 1rem 1rem 0;
  box-shadow: 0 8px 30px rgba(15, 23, 42, 0.16);
  padding: 1.25rem 1rem 1.5rem;
  z-index: 50;
  transform: translateX(-100%);
  visibility: hidden;
  transition:
    transform 220ms cubic-bezier(0.4, 0, 0.2, 1),
    visibility 220ms;
}

.filter-drawer.open {
  transform: translateX(0);
  visibility: visible;
}

@media (prefers-reduced-motion: reduce) {
  .filter-drawer {
    transition: none;
  }
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.6rem;
}

.drawer-close {
  border: none;
  background: none;
  font-size: 1.4rem;
  line-height: 1;
  color: var(--text-subtle);
  cursor: pointer;
  padding: 0.2rem 0.4rem;
}

.drawer-close:hover {
  color: var(--text-main);
}

.sidebar-body {
  width: 100%;
}

.sidebar-title {
  font-size: 0.95rem;
  color: var(--text-muted);
  margin: 0;
}

.filter-group {
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.7rem;
  margin-bottom: 0.7rem;
}

.filter-group-label {
  font-size: 0.85rem;
  font-weight: 700;
  margin-bottom: 0.4rem;
}

.filter-controls {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.4rem;
}

.mini-btn {
  flex: 1;
  font-size: 0.72rem;
  padding: 0.25rem 0;
  border: 1px solid var(--border-color);
  border-radius: 0.4rem;
  background: var(--card-bg);
  cursor: pointer;
}

.option-list {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.option-btn {
  font-size: 0.75rem;
  text-align: left;
  padding: 0.3rem 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: 0.4rem;
  background: var(--card-bg);
  color: var(--text-main);
  cursor: pointer;
}

.option-btn.active {
  background: var(--org-select-fill);
  border-color: var(--org-select-fill);
  color: var(--org-select-fill-text);
  font-weight: 700;
}

.selected-count {
  font-size: 0.7rem;
  color: var(--text-subtle);
  margin-top: 0.3rem;
}

.drawer-footer {
  border-top: 1px solid var(--border-color);
  padding-top: 0.7rem;
  margin-top: 0.3rem;
}

.admin-entry-btn {
  border: none;
  background: none;
  padding: 0.2rem 0;
  font-size: 0.72rem;
  color: var(--text-subtle);
  cursor: pointer;
}

.admin-entry-btn:hover {
  color: var(--text-main);
}
</style>
