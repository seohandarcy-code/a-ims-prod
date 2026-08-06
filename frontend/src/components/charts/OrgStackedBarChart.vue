<template>
  <EChart
    :option="option"
    height="340px"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DefaultLabelFormatterCallbackParams, EChartsOption } from 'echarts'
import EChart from './EChart.vue'

export interface StackedSeries {
  name: string
  data: number[]
  color: string
  unit?: string
}

const props = defineProps<{
  categories: string[]
  series: StackedSeries[]
  valueAxisName?: string
}>()

const option = computed<EChartsOption>(() => ({
  grid: { left: 90, right: 30, top: 40, bottom: 20 },
  legend: { top: 0 },
  xAxis: { type: 'value', name: props.valueAxisName ?? '' },
  yAxis: { type: 'category', data: props.categories, inverse: true },
  series: props.series.map((s) => ({
    name: s.name,
    type: 'bar' as const,
    stack: 'total',
    data: s.data,
    itemStyle: { color: s.color },
    label: {
      show: true,
      position: 'inside' as const,
      formatter: (p: DefaultLabelFormatterCallbackParams) => {
        const v = Number(p.value ?? 0)
        return v > 0 ? `${s.name} ${v.toLocaleString()}${s.unit ?? ''}` : ''
      },
    },
  })),
}))
</script>
