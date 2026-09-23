import { reactive, ref } from 'vue'
import { fetchMeta } from '../api/client'
import type { MetaResponse, OrgTreeNode } from '../types/api'

export type FilterKey = 'leader_opinion' | 'center_need'

const meta = ref<MetaResponse | null>(null)
const metaLoading = ref(false)
const metaError = ref<string | null>(null)

const selected = reactive<Record<FilterKey, string[]>>({
  leader_opinion: [],
  center_need: [],
})

// 조직 필터(팀→PJT→파트) 선택 상태 — 리프(파트)의 "PJT::파트" 복합키 flat 배열로만
// 저장한다. PJT/팀 단위의 전체/부분 선택 상태는 저장하지 않고 항상 이 배열에서 파생한다
// (상위 상태를 별도로 저장하면 desync 버그가 나기 쉽다는 설계 검토 결론).
const orgLeaf = reactive<string[]>([])

// "투자 진행 흐름 구분" 필터 선택 상태 — 옵션이 데이터 값이 아니라 종합현황 퍼널의 고정된
// key 목록(meta.flow_stage_options)이라 다른 필터들과 다른 별도 상태로 관리한다.
const selectedFlowStage = reactive<string[]>([])

const selectedOrg = ref<string>('')

let loaded = false

async function loadMeta(token?: string): Promise<void> {
  if (loaded) return
  loaded = true
  metaLoading.value = true
  metaError.value = null

  try {
    const data = await fetchMeta(token)
    meta.value = data

    selected.leader_opinion = [...data.filter_options.leader_opinion]
    selected.center_need = [...data.filter_options.center_need]

    orgLeaf.splice(0, orgLeaf.length, ...data.filter_options.part)
    selectedFlowStage.splice(0, selectedFlowStage.length, ...data.flow_stage_options.map((o) => o.key))

    selectedOrg.value = data.org_options[0] ?? ''
  } catch (err) {
    metaError.value = err instanceof Error ? err.message : String(err)
    loaded = false
  } finally {
    metaLoading.value = false
  }
}

function toggleOption(key: FilterKey, option: string): void {
  const list = selected[key]
  const idx = list.indexOf(option)
  if (idx >= 0) {
    list.splice(idx, 1)
  } else {
    list.push(option)
  }
}

function selectAll(key: FilterKey): void {
  if (!meta.value) return
  selected[key] = [...meta.value.filter_options[key]]
}

function clearAll(key: FilterKey): void {
  selected[key] = []
}

// ---- "투자 진행 흐름 구분" 필터 ----

function toggleFlowStage(key: string): void {
  const idx = selectedFlowStage.indexOf(key)
  if (idx >= 0) selectedFlowStage.splice(idx, 1)
  else selectedFlowStage.push(key)
}

function selectAllFlowStage(): void {
  if (!meta.value) return
  selectedFlowStage.splice(0, selectedFlowStage.length, ...meta.value.flow_stage_options.map((o) => o.key))
}

function clearAllFlowStage(): void {
  selectedFlowStage.splice(0, selectedFlowStage.length)
}

// ---- 조직 트리(팀/PJT/파트) 캐스케이딩 ----

function togglePart(partKey: string): void {
  const idx = orgLeaf.indexOf(partKey)
  if (idx >= 0) orgLeaf.splice(idx, 1)
  else orgLeaf.push(partKey)
}

function pjtPartKeys(pjtNode: OrgTreeNode): string[] {
  return (pjtNode.children ?? []).map((part) => part.key)
}

/** PJT 하위 파트 선택 개수를 바탕으로 전체선택/부분선택/미선택 상태를 파생한다(tri-state). */
function pjtSelectionState(pjtNode: OrgTreeNode): 'full' | 'half' | 'none' {
  const keys = pjtPartKeys(pjtNode)
  if (keys.length === 0) return 'none'
  const selectedCount = keys.filter((key) => orgLeaf.includes(key)).length
  if (selectedCount === 0) return 'none'
  if (selectedCount === keys.length) return 'full'
  return 'half'
}

/** PJT 행 클릭: 전체선택 상태면 하위 파트 전부 해제, 그 외에는 하위 파트 전부 선택. */
function togglePjt(pjtNode: OrgTreeNode): void {
  const keys = pjtPartKeys(pjtNode)
  const isFull = pjtSelectionState(pjtNode) === 'full'

  for (const key of keys) {
    const idx = orgLeaf.indexOf(key)
    if (isFull) {
      if (idx >= 0) orgLeaf.splice(idx, 1)
    } else if (idx < 0) {
      orgLeaf.push(key)
    }
  }
}

function selectAllOrg(): void {
  if (!meta.value) return
  orgLeaf.splice(0, orgLeaf.length, ...meta.value.filter_options.part)
}

function clearAllOrg(): void {
  orgLeaf.splice(0, orgLeaf.length)
}

export function useFilters() {
  return {
    meta,
    metaLoading,
    metaError,
    loadMeta,
    selected,
    selectedOrg,
    orgLeaf,
    selectedFlowStage,
    toggleOption,
    selectAll,
    clearAll,
    toggleFlowStage,
    selectAllFlowStage,
    clearAllFlowStage,
    togglePart,
    togglePjt,
    pjtSelectionState,
    selectAllOrg,
    clearAllOrg,
  }
}
