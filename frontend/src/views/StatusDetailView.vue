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
      <div class="section-title">
        단계별 상세 모니터링
      </div>
      <div class="sub-tab-bar">
        <button
          v-for="tab in subTabs"
          :key="tab.key"
          type="button"
          class="sub-tab-btn"
          :class="[tab.key, { active: activeSubTab === tab.key }]"
          @click="activeSubTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <div v-if="activeSubTab === 'review'">
        <MiniKpiGrid
          :cards="reviewCards"
          :columns="4"
        />
        <div class="two-col">
          <div>
            <div class="chart-subtitle">
              조직별 심의완료 건수
            </div>
            <div class="ratio-list">
              <InlineRatioBar
                v-for="row in data.review_monitoring.org_table"
                :key="row.org"
                :label="row.org"
                :filled="row.completed"
                :total="row.total"
                :color="STAGE.po"
              />
            </div>
          </div>
          <div>
            <div class="chart-subtitle">
              월별 누적 심의금액
            </div>
            <div class="panel-box">
              <!-- 막대가 나타내는 지표(월별 심의건수) 자체의 단계색을 사용: 심의 소프트 블루 -->
              <MonthlyComboChart
                :categories="data.review_monitoring.monthly_table.map((m) => String(m['월표시']))"
                bar-name="월별 심의건수"
                :bar-data="data.review_monitoring.monthly_table.map((m) => Number(m['심의건수'] ?? 0))"
                :bar-label-formatter="(v) => `${v.toLocaleString()}건`"
                :bar-color="STAGE.poSoft"
                :bar-label-color="STAGE.po"
                :lines="[
                  {
                    name: '누적 심의금액',
                    color: STAGE.po,
                    data: data.review_monitoring.monthly_table.map((m) => (m['누적심의금액_억원'] === null ? null : Number(m['누적심의금액_억원']))),
                    labelFormatter: (v) => `${v.toFixed(1)}억`,
                  },
                ]"
                left-axis-name="금액(억 원)"
                right-axis-name="심의건수(건)"
              />
            </div>
          </div>
        </div>
        <div class="panel-box">
          <SimpleRecordTable
            :columns="[
              { key: '월표시', label: '월' },
              { key: '심의건수', label: '월별 심의건수', format: 'int' },
              { key: '심의금액', label: '월별 심의금액', format: 'eok' },
              { key: '누적심의금액', label: '누적 심의금액', format: 'eok' },
            ]"
            :rows="data.review_monitoring.monthly_table"
          />
        </div>
      </div>

      <div v-else-if="activeSubTab === 'contract'">
        <MiniKpiGrid
          :cards="contractCards"
          :columns="4"
        />
        <div class="two-col">
          <div>
            <div class="chart-subtitle">
              조직별 계약건수
            </div>
            <div class="ratio-list">
              <InlineRatioBar
                v-for="row in data.contract_monitoring.org_table"
                :key="row.org"
                :label="row.org"
                :filled="row.registered"
                :total="row.total"
                :color="STAGE.contract"
              />
            </div>
          </div>
          <div>
            <div class="chart-subtitle">
              월별 누적 계약금액
            </div>
            <div class="panel-box">
              <!-- 막대가 나타내는 지표(월별 계약건수) 자체의 단계색을 사용: 계약 소프트 퍼플 -->
              <MonthlyComboChart
                :categories="data.contract_monitoring.monthly_table.map((m) => String(m['월표시']))"
                bar-name="월별 계약건수"
                :bar-data="data.contract_monitoring.monthly_table.map((m) => Number(m['계약건수'] ?? 0))"
                :bar-label-formatter="(v) => `${v.toLocaleString()}건`"
                :bar-color="STAGE.contractSoft"
                :bar-label-color="STAGE.contract"
                :lines="[
                  {
                    name: '누적 계약금액',
                    color: STAGE.contract,
                    data: data.contract_monitoring.monthly_table.map((m) => (m['누적계약금액_억원'] === null ? null : Number(m['누적계약금액_억원']))),
                    labelFormatter: (v) => `${v.toFixed(1)}억`,
                    labelPosition: 'top',
                  },
                ]"
                left-axis-name="금액(억 원)"
                right-axis-name="월별 계약건수(건)"
              />
            </div>
          </div>
        </div>
        <div class="panel-box">
          <SimpleRecordTable
            :columns="[
              { key: '월표시', label: '월' },
              { key: '계약건수', label: '월별 계약건수', format: 'int' },
              { key: '누적계약건수', label: '누적 계약건수', format: 'int' },
              { key: '누적계약금액', label: '누적 계약금액', format: 'eok' },
            ]"
            :rows="data.contract_monitoring.monthly_table"
          />
        </div>
      </div>

      <div v-else>
        <MiniKpiGrid
          :cards="executionCards"
          :columns="4"
        />
        <div class="two-col">
          <div>
            <div class="chart-subtitle">
              조직별 집행금액
            </div>
            <div class="ratio-list">
              <InlineRatioBar
                v-for="row in data.execution_monitoring.org_table"
                :key="row.org"
                :label="row.org"
                :filled="toEok(row.executed_amount)"
                :total="toEok(row.execution_po_amount)"
                unit="억"
                :decimals="1"
                :color="STAGE.execution"
              />
            </div>
          </div>
          <div>
            <div class="chart-subtitle">
              월별 누적 집행률
            </div>
            <div class="panel-box">
              <!-- 막대가 나타내는 지표(월별 집행금액) 자체의 단계색을 사용: 집행 소프트 그린 -->
              <MonthlyComboChart
                :categories="data.execution_monitoring.monthly_table.map((m) => String(m['월표시']))"
                bar-name="월별 집행금액"
                :bar-data="data.execution_monitoring.monthly_table.map((m) => toEok(m['기성금액']))"
                :bar-label-formatter="(v) => `${v.toFixed(1)}억`"
                :bar-color="STAGE.executionSoft"
                :bar-label-color="STAGE.execution"
                :lines="[
                  {
                    name: '누적 집행률',
                    color: STAGE.execution,
                    data: data.execution_monitoring.monthly_table.map((m) => (m['누적집행률'] === null ? null : Number(m['누적집행률']))),
                    labelFormatter: (v) => `${v.toFixed(1)}%`,
                  },
                ]"
                left-axis-name="누적집행률(%)"
                right-axis-name="집행금액(억 원)"
              />
            </div>
          </div>
        </div>
        <div class="panel-box">
          <SimpleRecordTable
            :columns="[
              { key: '월표시', label: '월' },
              { key: '기성금액', label: '월별 집행금액', format: 'eok' },
              { key: '누적기성금액', label: '누적 집행금액', format: 'eok' },
              { key: '누적집행률', label: '누적집행률', format: 'pct1' },
            ]"
            :rows="data.execution_monitoring.monthly_table"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useFilters } from '../composables/useFilters'
import { useStatusDetailData } from '../composables/useStatusDetailData'
import MiniKpiGrid, { type MiniKpiCard } from '../components/kpi/MiniKpiGrid.vue'
import MonthlyComboChart from '../components/charts/MonthlyComboChart.vue'
import SimpleRecordTable from '../components/table/SimpleRecordTable.vue'
import InlineRatioBar from '../components/charts/InlineRatioBar.vue'
import { STAGE } from '../theme/stageColors'

const { selected, selectedOrg, orgLeaf, selectedFlowStage } = useFilters()
const { data, loading, error } = useStatusDetailData(selected, selectedOrg, orgLeaf, selectedFlowStage)

const subTabs = [
  { key: 'review', label: '심의 상세 모니터링' },
  { key: 'contract', label: '계약 상세 모니터링' },
  { key: 'execution', label: '집행 상세 모니터링' },
] as const

const activeSubTab = ref<(typeof subTabs)[number]['key']>('review')

function toEok(value: unknown): number {
  const num = Number(value ?? 0)
  return Number.isFinite(num) ? Number((num / 100_000_000).toFixed(2)) : 0
}

const reviewCards = computed<MiniKpiCard[]>(() => {
  if (!data.value) return []
  const s = data.value.review_monitoring.summary
  return [
    { label: '심의 대상건수', value: `${s.total_count.toLocaleString()} 건`, tone: 'po' },
    { label: '심의완료 건수', value: `${s.review_done_count.toLocaleString()} 건`, tone: 'po' },
    { label: '심의완료율', value: `${s.review_completion_rate.toFixed(1)}%`, tone: s.review_completion_rate >= 80 ? 'good' : 'po' },
    { label: '심의 대기건', value: `${s.review_pending_count.toLocaleString()} 건`, tone: s.review_pending_count > 0 ? 'po' : 'good' },
  ]
})

const contractCards = computed<MiniKpiCard[]>(() => {
  if (!data.value) return []
  const s = data.value.contract_monitoring.summary
  return [
    { label: '계약대상 건수', value: `${s.review_done_count.toLocaleString()} 건`, tone: 'contract' },
    { label: '계약완료 건수', value: `${s.contract_count.toLocaleString()} 건`, tone: 'contract' },
    { label: '계약완료율', value: `${s.review_to_contract_rate.toFixed(1)}%`, tone: s.review_to_contract_rate >= 80 ? 'good' : 'contract' },
    { label: '계약 대기건', value: `${s.contract_backlog_count.toLocaleString()} 건`, tone: s.contract_backlog_count > 0 ? 'contract' : 'good' },
  ]
})

const executionCards = computed<MiniKpiCard[]>(() => {
  if (!data.value) return []
  const s = data.value.execution_monitoring.summary
  return [
    { label: '계약금액', value: `${toEok(s.execution_po_sum)} 억`, tone: 'execution' },
    { label: '집행금액', value: `${toEok(s.executed_sum)} 억`, tone: 'execution' },
    { label: '계약 집행율', value: `${s.amount_execution_rate.toFixed(1)}%`, tone: s.amount_execution_rate >= 70 ? 'good' : 'execution' },
    { label: '집행 완료건', value: `${s.investment_done_count.toLocaleString()} 건`, tone: 'execution' },
  ]
})
</script>

<style scoped>
.ratio-list {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--card-radius);
  padding: 1.1rem 1.2rem;
  box-shadow: var(--shadow);
}

.panel-box {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--card-radius);
  padding: 1.1rem 1.2rem;
  box-shadow: var(--shadow);
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1.6fr;
  gap: 1.2rem;
  margin-bottom: 1.4rem;
}

.sub-tab-bar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.sub-tab-btn {
  padding: 0.5rem 1rem;
  border: 1px solid var(--border-color);
  border-radius: 0.6rem;
  background: var(--card-bg);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}

.sub-tab-btn.review.active {
  background: var(--stage-po-color);
  border-color: var(--stage-po-color);
  color: #fff;
}

.sub-tab-btn.contract.active {
  background: var(--stage-contract-color);
  border-color: var(--stage-contract-color);
  color: #fff;
}

.sub-tab-btn.execution.active {
  background: var(--stage-execution-color);
  border-color: var(--stage-execution-color);
  color: #fff;
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
