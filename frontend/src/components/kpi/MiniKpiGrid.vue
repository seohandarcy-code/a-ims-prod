<template>
  <div
    class="kpi-grid"
    :style="{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }"
  >
    <div
      v-for="card in cards"
      :key="card.label"
      class="kpi-card"
      :class="[`tone-${card.tone ?? 'normal'}`, { dense, 'has-foot': !!card.secondary }]"
      :title="card.tooltip ?? card.caption"
    >
      <div class="kpi-body">
        <div class="kpi-label">
          {{ card.label }}
        </div>
        <div
          class="kpi-value"
          :class="{ 'kpi-value-lg': card.emphasizeValue }"
        >
          {{ normalize(card.value).number }}<span
            v-if="normalize(card.value).unit"
            class="kpi-unit"
          >{{ normalize(card.value).unit }}</span>
        </div>
        <div
          v-if="card.caption && !dense"
          class="kpi-caption"
        >
          {{ card.caption }}
        </div>
      </div>
      <div
        v-if="card.secondary"
        class="kpi-foot"
      >
        <span class="kpi-foot-label">{{ card.secondaryLabel ?? '금액' }}</span>
        <span class="kpi-foot-value">{{ secondaryText(card.secondary) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface KpiValue {
  number: string
  unit?: string
}

export interface MiniKpiCard {
  label: string
  value: string | KpiValue
  secondary?: string | KpiValue
  /** 풋 스트립 좌측 미니 라벨. 지정하지 않으면 '금액'. */
  secondaryLabel?: string
  caption?: string
  tooltip?: string
  tone?: 'normal' | 'good' | 'warn' | 'bad' | 'po' | 'contract' | 'execution' | 'total' | 'total-light'
  /** 건수형 카드의 값 숫자를 더 크게 강조해서 보여준다 (%/비율 카드는 적용하지 않음). */
  emphasizeValue?: boolean
}

withDefaults(defineProps<{ cards: MiniKpiCard[]; columns?: number; dense?: boolean }>(), { columns: 4, dense: false })

function normalize(value: string | KpiValue): KpiValue {
  return typeof value === 'string' ? { number: value } : value
}

function secondaryText(value: string | KpiValue): string {
  const v = normalize(value)
  return v.unit ? `${v.number}${v.unit}` : v.number
}
</script>

<style scoped>
.kpi-grid {
  display: grid;
  gap: 0.85rem;
  margin: 0.35rem 0 0.8rem;
}

.kpi-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 0.9rem;
  box-shadow: var(--shadow);
  padding: 0.95rem 1rem;
  min-height: 7rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
}

.kpi-card.has-foot {
  justify-content: flex-start;
  padding-bottom: 0;
}

.tone-good,
.tone-warn,
.tone-bad,
.tone-po,
.tone-contract,
.tone-execution,
.tone-total,
.tone-total-light {
  border-color: var(--border-color);
  padding-left: 1.25rem;
}

.tone-good { border-left: 8px solid var(--tone-good-border); }
.tone-warn { border-left: 8px solid var(--tone-warn-border); }
.tone-bad { border-left: 8px solid var(--tone-bad-border); }
.tone-po { border-left: 8px solid var(--tone-po-border); }
.tone-contract { border-left: 8px solid var(--tone-contract-border); }
.tone-execution { border-left: 8px solid var(--tone-execution-border); }
.tone-total { border-left: 8px solid var(--tone-total-border); }
.tone-total-light { border-left: 8px solid var(--tone-total-light-border); }

.kpi-card.dense {
  min-height: 5.2rem;
  padding: 0.75rem 0.9rem;
}

.kpi-card.dense.tone-good,
.kpi-card.dense.tone-warn,
.kpi-card.dense.tone-bad,
.kpi-card.dense.tone-po,
.kpi-card.dense.tone-contract,
.kpi-card.dense.tone-execution,
.kpi-card.dense.tone-total,
.kpi-card.dense.tone-total-light {
  padding-left: 1.15rem;
}

.kpi-label {
  font-size: 0.9rem;
  color: var(--text-muted);
  font-weight: 700;
  margin-bottom: 0.3rem;
}

.kpi-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.kpi-value {
  font-size: 1.7rem;
  line-height: 1.15;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--text-main);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.kpi-value-lg {
  font-size: 2rem;
}

.kpi-unit {
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: normal;
  color: var(--text-muted);
  margin-left: 0.3em;
}

.kpi-caption {
  font-size: 0.75rem;
  color: var(--text-subtle);
  margin-top: 0.3rem;
  line-height: 1.3;
}

/* ===== D안: 풋 스트립 분리형 (금액을 하단 각주 띠로 물리 분할) ===== */

.kpi-foot {
  margin: 0.85rem -1rem 0;
  padding: 0.4rem 1rem;
  background: var(--neutral-soft);
  border-top: 1px dashed var(--border-color);
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.tone-good.has-foot .kpi-foot,
.tone-warn.has-foot .kpi-foot,
.tone-bad.has-foot .kpi-foot,
.tone-po.has-foot .kpi-foot,
.tone-contract.has-foot .kpi-foot,
.tone-execution.has-foot .kpi-foot,
.tone-total.has-foot .kpi-foot,
.tone-total-light.has-foot .kpi-foot {
  margin-left: -1.25rem;
}

.kpi-foot-label {
  font-size: 0.68rem;
  font-weight: 500;
  color: var(--text-subtle);
}

.kpi-foot-value {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
</style>
