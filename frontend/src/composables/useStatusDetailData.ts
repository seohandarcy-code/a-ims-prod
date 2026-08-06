import { ref, watch, type Ref } from 'vue'
import { fetchStatusDetail } from '../api/client'
import type { CommonFilterParams, StatusDetailResponse } from '../types/api'
import { useAdminAuth } from './useAdminAuth'
import type { FilterKey } from './useFilters'

export function useStatusDetailData(
  selected: Record<FilterKey, string[]>,
  selectedOrg: Ref<string>,
  orgLeaf: string[],
  selectedFlowStage: string[],
) {
  const data = ref<StatusDetailResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { dataVersion } = useAdminAuth()

  async function load(): Promise<void> {
    if (!selectedOrg.value) return
    loading.value = true
    error.value = null

    const params: CommonFilterParams = {
      part: orgLeaf,
      leader_opinion: selected.leader_opinion,
      center_need: selected.center_need,
      flow_stage: selectedFlowStage,
      selected_org: selectedOrg.value,
    }

    try {
      data.value = await fetchStatusDetail(params)
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
    } finally {
      loading.value = false
    }
  }

  watch(
    [
      orgLeaf,
      () => selected.leader_opinion,
      () => selected.center_need,
      selectedFlowStage,
      selectedOrg,
      dataVersion,
    ],
    load,
    { immediate: true, deep: true },
  )

  return { data, loading, error, reload: load }
}
