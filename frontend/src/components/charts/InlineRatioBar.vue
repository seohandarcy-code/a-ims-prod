<template>
  <div class="ratio-row">
    <div class="ratio-label">
      {{ label }}
    </div>
    <div
      class="ratio-track"
      :style="trackHeight ? { height: trackHeight } : undefined"
    >
      <div
        class="ratio-fill"
        :style="{ width: `${clampedPct}%`, background: color }"
      >
        <span
          v-if="showInside"
          class="ratio-fill-label"
        >{{ formatNumber(filled) }}{{ unit }}<template v-if="showPercent"> · {{ clampedPct.toFixed(1) }}%</template></span>
      </div>
      <span
        v-if="!showInside"
        class="ratio-outside-label"
        :style="{ left: `calc(${clampedPct}% + 8px)` }"
      >{{ formatNumber(filled) }}{{ unit }}<template v-if="showPercent"> · {{ clampedPct.toFixed(1) }}%</template></span>
    </div>
    <div class="ratio-total">
      {{ formatNumber(total) }}{{ unit }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const INSIDE_LABEL_THRESHOLD = 25

const props = withDefaults(
  defineProps<{
    label: string
    filled: number
    total: number
    unit?: string
    color: string
    decimals?: number
    showPercent?: boolean
    /** 트랙(막대) 두께 오버라이드. 미지정 시 기본 CSS 값(1.5rem) 유지 — 기존 화면 영향 없음. */
    trackHeight?: string
  }>(),
  { unit: '건', showPercent: false, decimals: undefined, trackHeight: undefined },
)

const pct = computed(() => (props.total > 0 ? (props.filled / props.total) * 100 : 0))
const clampedPct = computed(() => Math.max(0, Math.min(100, pct.value)))
const showInside = computed(() => pct.value >= INSIDE_LABEL_THRESHOLD)

function formatNumber(n: number): string {
  if (props.decimals === undefined) return n.toLocaleString()
  return n.toLocaleString(undefined, {
    minimumFractionDigits: props.decimals,
    maximumFractionDigits: props.decimals,
  })
}
</script>

<style scoped>
.ratio-row {
  display: grid;
  grid-template-columns: 110px 1fr 64px;
  align-items: center;
  gap: 0.9rem;
  margin-bottom: 1rem;
}

.ratio-row:last-child {
  margin-bottom: 0;
}

.ratio-label {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-main);
}

.ratio-track {
  position: relative;
  height: 1.5rem;
  background: var(--unexecuted-color);
  border-radius: 0.5rem;
  overflow: visible;
}

.ratio-fill {
  height: 100%;
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 0.5rem;
  overflow: hidden;
}

.ratio-fill-label {
  color: #fff;
  font-size: 0.76rem;
  font-weight: 700;
  white-space: nowrap;
}

.ratio-outside-label {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-main);
  font-size: 0.76rem;
  font-weight: 700;
  white-space: nowrap;
}

.ratio-total {
  font-size: 0.82rem;
  color: var(--text-muted);
  font-weight: 600;
  text-align: right;
}
</style>
