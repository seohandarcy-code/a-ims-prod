<template>
  <div
    ref="el"
    :style="{ width: '100%', height: height }"
  />
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    option: echarts.EChartsOption
    height?: string
  }>(),
  { height: '320px' },
)

const emit = defineEmits<{ click: [params: echarts.ECElementEvent] }>()

const el = ref<HTMLDivElement | null>(null)
const chart = shallowRef<echarts.ECharts | null>(null)

function resize(): void {
  chart.value?.resize()
}

onMounted(() => {
  if (!el.value) return
  chart.value = echarts.init(el.value)
  chart.value.setOption(props.option)
  chart.value.on('click', (params) => emit('click', params as echarts.ECElementEvent))
  window.addEventListener('resize', resize)
})

watch(
  () => props.option,
  (next) => {
    chart.value?.setOption(next, { notMerge: true })
  },
  { deep: true },
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart.value?.dispose()
})
</script>
