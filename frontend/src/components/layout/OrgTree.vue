<template>
  <div class="org-tree">
    <template
      v-for="team in nodes"
      :key="team.key"
    >
      <div
        class="tree-row tree-team"
        :class="{ clickable: teamClickable, active: mode === 'single' && modelValue === team.key }"
        @click="teamClickable && onNodeClick(team)"
      >
        <span class="row-label">{{ team.label }}</span>
      </div>

      <div class="tree-group">
        <template
          v-for="pjt in team.children ?? []"
          :key="pjt.key"
        >
          <button
            type="button"
            class="tree-row tree-pjt"
            :class="pjtClass(pjt)"
            :style="pjtStyle(pjt)"
            @click="onPjtClick(pjt)"
          >
            <span class="row-label">{{ pjt.label }}</span>
            <span class="pjt-right">
              <span
                v-if="mode === 'multi'"
                class="count-chip"
              >{{ pjtCountLabel(pjt) }}</span>
              <span
                v-if="collapsible"
                class="chevron"
                :class="{ open: isExpanded(pjt) }"
                @click="toggleExpand(pjt, $event)"
              >▾</span>
            </span>
          </button>

          <div
            v-if="isExpanded(pjt)"
            class="tree-group tree-parts"
          >
            <button
              v-for="part in pjt.children ?? []"
              :key="part.key"
              type="button"
              class="tree-row tree-part"
              :class="{ active: partActive(part) }"
              @click="onPartClick(part)"
            >
              {{ part.label }}
            </button>
          </div>
        </template>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import type { OrgTreeNode } from '../../types/api'
import { useFilters } from '../../composables/useFilters'

const props = defineProps<{
  nodes: OrgTreeNode[]
  mode: 'single' | 'multi'
  modelValue?: string
  collapsible?: boolean
}>()

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const { orgLeaf, togglePart, togglePjt, pjtSelectionState } = useFilters()

// 팀 레벨 렌더 규칙:
// - single(대시보드): 팀이 "전체" 스코프 버튼을 겸하므로 노드 개수와 무관하게 항상 클릭 가능.
// - multi(드로어): 노드가 1개면 헤더(클릭 불가), 2개 이상이면 선택 가능 노드로 자동 승격된다.
const teamClickable = computed(() => (props.mode === 'single' ? true : props.nodes.length > 1))

function onNodeClick(node: OrgTreeNode): void {
  emit('update:modelValue', node.key)
}

function onPjtClick(pjt: OrgTreeNode): void {
  if (props.mode === 'single') {
    onNodeClick(pjt)
    return
  }
  togglePjt(pjt)
}

function pjtClass(pjt: OrgTreeNode): Record<string, boolean> {
  if (props.mode === 'single') {
    return { active: props.modelValue === pjt.key }
  }
  return {}
}

function pjtStyle(pjt: OrgTreeNode): Record<string, string> {
  if (props.mode === 'multi') {
    const state = pjtSelectionState(pjt)
    if (state === 'full') return { '--rail-top': '0%', '--rail-height': '100%' }
    if (state === 'half') return { '--rail-top': '25%', '--rail-height': '50%' }
    return {}
  }

  // single(대시보드): 선택된 파트가 이 PJT 하위에 있으면 "여기에 선택이 있다"는 막대를 보여준다.
  const hasSelectedPart = (pjt.children ?? []).some((part) => part.key === props.modelValue)
  return hasSelectedPart ? { '--rail-top': '0%', '--rail-height': '100%' } : {}
}

function onPartClick(part: OrgTreeNode): void {
  if (props.mode === 'single') {
    onNodeClick(part)
    return
  }
  togglePart(part.key)
}

function partActive(part: OrgTreeNode): boolean {
  if (props.mode === 'single') return props.modelValue === part.key
  return orgLeaf.includes(part.key)
}

function pjtCountLabel(pjt: OrgTreeNode): string {
  const total = pjt.children?.length ?? 0
  const selectedCount = (pjt.children ?? []).filter((part) => orgLeaf.includes(part.key)).length
  return `${selectedCount}/${total}`
}

// 드로어 접기: meta 로드 시(=nodes가 처음 채워질 때) 딱 1번만 초기 펼침 상태를 계산한다.
// 이후 클릭으로 인한 재계산은 하지 않는다 — 마지막 파트를 선택하는 순간 행이 접히는
// 인터랙션을 피하기 위함(디자인 리뷰에서 명시적으로 지적된 지점).
// 미선택(none) 상태인 PJT만 접고 나머지(전체/부분 선택)는 펼쳐서 시작한다 — 기본값이
// 전체선택이라 "half만 펼침"으로는 파트 체크박스 자체가 안 보이는 문제가 있었다.
const expandedPjt = reactive(new Set<string>())
let expandInitialized = false

function initExpansion(): void {
  if (expandInitialized || !props.collapsible || !props.nodes.length) return
  expandInitialized = true
  for (const team of props.nodes) {
    for (const pjt of team.children ?? []) {
      if (pjtSelectionState(pjt) !== 'none') {
        expandedPjt.add(pjt.key)
      }
    }
  }
}

watch(() => props.nodes, initExpansion, { immediate: true })

function isExpanded(pjt: OrgTreeNode): boolean {
  if (!props.collapsible) return true
  return expandedPjt.has(pjt.key)
}

function toggleExpand(pjt: OrgTreeNode, event: Event): void {
  event.stopPropagation()
  if (expandedPjt.has(pjt.key)) expandedPjt.delete(pjt.key)
  else expandedPjt.add(pjt.key)
}
</script>

<style scoped>
.org-tree {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.tree-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
  width: 100%;
  text-align: left;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  background: transparent;
  font: inherit;
  padding: 0.4rem 0.6rem;
  box-sizing: border-box;
}

.row-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.tree-team {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--text-subtle);
  cursor: default;
}

.tree-team.clickable {
  cursor: pointer;
  color: var(--text-main);
  border-color: var(--border-color);
}

.tree-team.active {
  background: var(--org-select-fill);
  border-color: var(--org-select-fill);
  color: var(--org-select-fill-text);
}

.tree-pjt {
  position: relative;
  cursor: pointer;
  padding-left: calc(0.6rem + var(--tree-indent-2));
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-main);
  border-color: var(--border-color);
}

.tree-pjt::before {
  content: '';
  position: absolute;
  left: 0.15rem;
  top: var(--rail-top, 50%);
  height: var(--rail-height, 0%);
  width: 3px;
  border-radius: 999px;
  background: var(--org-select-fill);
}

.tree-pjt.active {
  background: var(--org-select-fill);
  border-color: var(--org-select-fill);
  color: var(--org-select-fill-text);
}

.pjt-right {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.count-chip {
  font-size: 0.65rem;
  color: var(--text-subtle);
  font-variant-numeric: tabular-nums;
}

.chevron {
  font-size: 0.65rem;
  color: var(--text-subtle);
  transition: transform 0.15s ease;
  cursor: pointer;
  padding: 0.1rem;
}

.chevron.open {
  transform: rotate(180deg);
}

.tree-parts {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  margin: 0.15rem 0 0.35rem calc(0.6rem + var(--tree-indent-2));
  padding-left: 0.5rem;
  border-left: 1px solid var(--tree-rail-color);
}

.tree-part {
  cursor: pointer;
  padding: 0.3rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-muted);
  border-color: transparent;
}

.tree-part.active {
  background: var(--org-select-fill);
  border-color: var(--org-select-fill);
  color: var(--org-select-fill-text);
  font-weight: 700;
}

@media (prefers-reduced-motion: reduce) {
  .chevron {
    transition: none;
  }
}
</style>
