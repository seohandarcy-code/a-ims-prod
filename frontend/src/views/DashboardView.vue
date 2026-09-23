<template>
  <div>
    <div
      v-if="loading && !data"
      class="loading"
    >
      불러오는 중...
    </div>
    <div
      v-else-if="error"
      class="error"
    >
      {{ error }}
    </div>

    <template v-else-if="data">
      <MiniKpiGrid
        :cards="kpiCards"
        :columns="6"
      />

      <div class="org-and-charts">
        <div>
          <div class="chart-subtitle">
            조직 구분
          </div>
          <div class="panel-box">
            <div class="panel-context">
              선택된 조직: <b>{{ selectedOrgLabel }}</b>
            </div>
            <OrgTree
              v-model="selectedOrg"
              mode="single"
              :nodes="meta?.org_tree ?? []"
            />
          </div>
        </div>
        <div class="charts-col">
          <div>
            <div class="chart-subtitle">
              투자 진행 흐름 구분
            </div>
            <div class="panel-box">
              <div class="org-hint">
                투자 진행 구분 명칭 및 막대를 클릭하면 상세 리스트가 해당 항목으로 필터링됩니다. 다시 클릭하면 필터가 해제됩니다.
              </div>
              <StageExpandedWaterfallChart
                :items="data.progress_funnel"
                :selected-key="selectedFunnelKey"
                @select="onFunnelSelect"
              />
            </div>
          </div>
          <div>
            <div class="chart-subtitle">
              월별 진행 흐름 구분
            </div>
            <div class="panel-box">
              <div class="org-hint">
                월별 구분 명칭을 클릭하면 상세 리스트가 해당 항목으로 필터링됩니다. 다시 클릭하면 필터가 해제됩니다.
              </div>
              <!-- 누적 심의/계약/집행 금액 3종 라인 — 종합현황 KPI와 동일한 단계색을 사용 -->
              <MonthlyComboChart
                :categories="monthLabels"
                :lines="monthlyLines"
                :reference-line="referenceLine"
                left-axis-name="금액(억 원)"
                :selected-month="selectedMonthKey"
                @select="onMonthSelect"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="chart-subtitle">
        상세 리스트
      </div>
      <div class="panel-box">
        <div class="org-hint">
          조직, 투자 진행 흐름, 월별 진행 흐름 구분에 따른 상세리스트를 보여줍니다.
        </div>
        <DetailTable
          :columns="data.detail_columns"
          :search-keys="data.detail_search_keys"
          :rows="data.detail_rows"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useFilters } from '../composables/useFilters'
import { useDashboardData } from '../composables/useDashboardData'
import OrgTree from '../components/layout/OrgTree.vue'
import MiniKpiGrid, { type MiniKpiCard } from '../components/kpi/MiniKpiGrid.vue'
import StageExpandedWaterfallChart from '../components/charts/StageExpandedWaterfallChart.vue'
import MonthlyComboChart, { type ComboLineSeries, type ReferenceLine } from '../components/charts/MonthlyComboChart.vue'
import DetailTable from '../components/table/DetailTable.vue'
import { STAGE } from '../theme/stageColors'

const { selected, selectedOrg, meta, orgLeaf, selectedFlowStage } = useFilters()
const selectedFunnelKey = ref<string | null>(null)
const selectedMonthKey = ref<number | null>(null)
const { data, loading, error } = useDashboardData(selected, selectedOrg, orgLeaf, selectedFlowStage, selectedFunnelKey, selectedMonthKey)

function onFunnelSelect(key: string): void {
  selectedFunnelKey.value = selectedFunnelKey.value === key ? null : key
}

function onMonthSelect(month: number): void {
  selectedMonthKey.value = selectedMonthKey.value === month ? null : month
}

// 조직 트리 key 형태: 전체="A-Infra기술팀"(=org_options[0]), PJT="시스템_PJT", 파트="PJT::파트" 복합키.
const selectedOrgLabel = computed(() => {
  const org = selectedOrg.value
  const totalKey = meta.value?.org_options[0]
  if (!org) return '-'
  if (org === totalKey) return meta.value?.team_name ?? org
  if (org.includes('::')) {
    const [, part] = org.split('::')
    return part
  }
  return org
})

const kpiCards = computed<MiniKpiCard[]>(() => {
  if (!data.value) return []
  const k = data.value.executive_kpi
  return [
    {
      label: '전체 투자계획',
      value: { number: k.total_count.toLocaleString(), unit: '건' },
      secondary: {
        number: (k.invest_sum / 100_000_000).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
        unit: '억',
      },
      caption: '계획 + 계획외 + 타팀이관 + Drop',
      tone: 'total',
      emphasizeValue: true,
    },
    {
      label: '진행 투자계획',
      value: { number: k.progress_count.toLocaleString(), unit: '건' },
      secondary: {
        number: (k.progress_sum / 100_000_000).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
        unit: '억',
      },
      caption: '계획 + 계획외',
      tone: 'total-light',
      emphasizeValue: true,
    },
    {
      label: '심의 완료',
      value: { number: k.review_count.toLocaleString(), unit: '건' },
      secondary: {
        number: (k.review_sum / 100_000_000).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
        unit: '억',
      },
      caption: '진행투자계획 중, 센터심의완료 (5억↓ 팀)',
      tone: 'po',
      emphasizeValue: true,
    },
    {
      label: '계약 완료',
      value: { number: k.contract_done_count.toLocaleString(), unit: '건' },
      secondary: {
        number: (k.contract_done_sum / 100_000_000).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
        unit: '억',
      },
      caption: '심의완료건 중, ERP등록 또는 계약',
      tone: 'contract',
      emphasizeValue: true,
    },
    {
      label: '투자 완료',
      value: { number: k.investment_done_count.toLocaleString(), unit: '건' },
      secondary: {
        number: (k.investment_done_sum / 100_000_000).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
        unit: '억',
      },
      caption: '계약완료건 중, 정산 완료',
      tone: 'execution',
      emphasizeValue: true,
    },
    {
      label: '투자 집행율',
      value: { number: k.amount_execution_rate.toFixed(1), unit: '%' },
      secondaryGroup: [
        {
          label: '집행금액',
          number: (k.execution_settled_sum / 100_000_000).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
          unit: '억',
        },
        {
          label: '계약금액',
          number: (k.contract_done_sum / 100_000_000).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
          unit: '억',
        },
      ],
      caption: '집행금액 / 계약금액',
      tone: 'execution',
    },
  ]
})

const monthLabels = computed(() => data.value?.monthly_flow.map((m) => String(m['월표시'])) ?? [])

// 전체 투자계획 금액(계획+계획외+타팀이관+Drop) 기준선 — 상단 KPI "전체 투자계획" 카드와 동일한 값.
const NEUTRAL_LINE = '#595870'

const monthlyLines = computed<ComboLineSeries[]>(() => {
  if (!data.value) return []
  return [
    {
      name: '누적 심의금액',
      data: data.value.monthly_flow.map((m) => (m['누적심의금액_억원'] === null ? null : Number(m['누적심의금액_억원']))),
      color: STAGE.po,
      lineType: 'solid',
      labelFormatter: (v) => `${v.toFixed(1)}억`,
      labelPosition: 'top',
    },
    {
      name: '누적 계약금액',
      data: data.value.monthly_flow.map((m) => (m['누적계약금액_억원'] === null ? null : Number(m['누적계약금액_억원']))),
      color: STAGE.contract,
      lineType: 'dashed',
      labelFormatter: (v) => `${v.toFixed(1)}억`,
      labelPosition: 'top',
    },
    {
      name: '누적 집행금액',
      data: data.value.monthly_flow.map((m) => (m['누적기성금액_억원'] === null ? null : Number(m['누적기성금액_억원']))),
      color: STAGE.execution,
      lineType: 'dotted',
      labelFormatter: (v) => `${v.toFixed(1)}억`,
      labelPosition: 'bottom',
    },
  ]
})

// "전체 투자계획 금액" 기준선은 더 이상 매월 반복되는 데이터 포인트 라인이 아니라 markLine으로
// 그린다 — 그리드 끝(마디)까지 선이 이어지고 그 뒤에 값 라벨이 붙는다(2026-08-11 오너 요청).
const referenceLine = computed<ReferenceLine | undefined>(() => {
  if (!data.value) return undefined
  return {
    value: data.value.executive_kpi.invest_sum / 100_000_000,
    color: NEUTRAL_LINE,
    formatter: (v) => `${v.toFixed(1)}억`,
    name: '전체 투자계획 금액',
  }
})
</script>

<style scoped>
.org-and-charts {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  align-items: start;
  gap: 0.85rem;
  margin-bottom: 1.4rem;
}

.charts-col {
  grid-column: span 5;
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
  min-width: 0;
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1.6fr;
  align-items: stretch;
  gap: 1.2rem;
  margin-bottom: 1.4rem;
}

.panel-box {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--card-radius);
  padding: 1.1rem 1.2rem;
  box-shadow: var(--shadow);
}

.org-hint {
  margin-bottom: 0.9rem;
  font-size: 0.72rem;
  line-height: 1.5;
  color: var(--text-subtle);
}

.panel-context {
  font-size: 0.78rem;
  color: var(--text-subtle);
  margin-bottom: 0.35rem;
}

.panel-context b {
  color: var(--text-main);
  font-weight: 700;
}

.loading,
.error {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
}

.error {
  color: var(--tone-bad-border);
}
</style>
