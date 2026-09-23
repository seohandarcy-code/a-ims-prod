import { ref, watch, type Ref } from 'vue'
import { fetchDashboard } from '../api/client'
import type { CommonFilterParams, DashboardResponse } from '../types/api'
import { useAdminAuth } from './useAdminAuth'
import type { FilterKey } from './useFilters'

export function useDashboardData(
  selected: Record<FilterKey, string[]>,
  selectedOrg: Ref<string>,
  orgLeaf: string[],
  selectedFlowStage: string[],
  selectedFunnelKey: Ref<string | null>,
  selectedMonthKey: Ref<number | null>,
) {
  const data = ref<DashboardResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { dataVersion, token } = useAdminAuth()

  async function load(): Promise<void> {
    if (!selectedOrg.value) return
    loading.value = true
    error.value = null

    const params: CommonFilterParams = {
      // 파트 선택이 PJT를 완전히 함의하므로 org는 중복 전송하지 않는다.
      part: orgLeaf,
      leader_opinion: selected.leader_opinion,
      center_need: selected.center_need,
      flow_stage: selectedFlowStage,
      selected_org: selectedOrg.value,
      funnel_key: selectedFunnelKey.value ?? undefined,
      month_key: selectedMonthKey.value ?? undefined,
    }

    try {
      data.value = await fetchDashboard(params, token.value ?? undefined)
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
      selectedFunnelKey,
      selectedMonthKey,
      dataVersion,
    ],
    load,
    { immediate: true, deep: true },
  )

  return { data, loading, error, reload: load }
}
