<template>
  <EChart
    :option="option"
    height="340px"
    @click="onChartClick"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DefaultLabelFormatterCallbackParams, ECElementEvent, EChartsOption } from 'echarts'
import EChart from './EChart.vue'

export interface ComboLineSeries {
  name: string
  data: (number | null)[]
  color: string
  /** 선 스타일. 기본값 'solid'. 같은 차트에 색만으로 구분하기 애매한 라인이 여럿일 때 'dashed'/'dotted'로 구분한다. */
  lineType?: 'solid' | 'dashed' | 'dotted'
  labelFormatter?: (value: number) => string
  labelPosition?: 'top' | 'bottom' | 'right'
  /** 월별 원형 마커 표시 여부. 기본값 true. 기준선처럼 마커가 불필요한 라인은 false로 끈다. */
  showSymbol?: boolean
  /** true면 값 라벨을 마지막 데이터 포인트에만 표시한다(기준선처럼 매월 반복 표시가 불필요할 때). */
  labelOnlyLast?: boolean
}

const props = defineProps<{
  categories: string[]
  barName?: string
  barData?: number[]
  lines: ComboLineSeries[]
  leftAxisName?: string
  rightAxisName?: string
  barLabelFormatter?: (value: number) => string
  barColor?: string
  /** 막대 라벨 색. barColor는 옅은 배경용 색이라 그대로 쓰면 라벨이 막대에 묻히므로,
   * 해당 지표의 진한 단계색(STAGE.po/contract/execution)을 명시적으로 전달한다. */
  barLabelColor?: string
  selectedMonth?: number | null
}>()

const emit = defineEmits<{ select: [month: number] }>()

const EMPHASIS_COLOR = '#595870'

const hasBar = computed(() => !!props.barName && !!props.barData && props.barData.length > 0)

function barLabel(p: DefaultLabelFormatterCallbackParams): string {
  const v = Number(p.value ?? 0)
  if (!v) return ''
  return props.barLabelFormatter ? props.barLabelFormatter(v) : String(v)
}

function lineLabel(line: ComboLineSeries, p: DefaultLabelFormatterCallbackParams): string {
  const raw = p.value
  if (raw === null || raw === undefined || raw === '') return ''
  if (line.labelOnlyLast && typeof p.dataIndex === 'number' && p.dataIndex !== line.data.length - 1) return ''
  const v = Number(raw)
  if (!v) return ''
  return line.labelFormatter ? line.labelFormatter(v) : String(v)
}

function monthFromLabel(label: string): number | null {
  const match = /^(\d+)월$/.exec(label)
  return match ? Number(match[1]) : null
}

// 월 필터링은 x축의 월 명칭을 클릭할 때만 동작한다(막대/라인 마크 클릭으로는 동작하지 않음).
function onChartClick(params: ECElementEvent): void {
  if (params.componentType !== 'xAxis') return
  const month = monthFromLabel(String(params.value ?? ''))
  if (month !== null) emit('select', month)
}

const option = computed<EChartsOption>(() => ({
  // right는 'right' 위치 라벨(예: 기준선 라벨)이 잘리지 않을 최소한만 확보한다 —
  // 기존 95px은 필요 이상으로 넓어 좌우 여백이 어긋나 보였다(2026-08-10 오너 피드백).
  grid: { left: 55, right: 68, top: 55, bottom: 60 },
  legend: { top: 0 },
  xAxis: {
    type: 'category',
    data: props.categories.map((c) => ({
      value: c,
      textStyle:
        monthFromLabel(c) === props.selectedMonth
          ? { color: EMPHASIS_COLOR, fontWeight: 700 }
          : undefined,
    })),
    axisLabel: { margin: 24, triggerEvent: true },
    triggerEvent: true,
  },
  yAxis: hasBar.value
    ? [
        { type: 'value', name: props.leftAxisName ?? '', position: 'left' },
        { type: 'value', name: props.rightAxisName ?? '', position: 'right', splitLine: { show: false } },
      ]
    : [{ type: 'value', name: props.leftAxisName ?? '', position: 'left' }],
  series: [
    ...(hasBar.value
      ? [
          {
            name: props.barName,
            type: 'bar' as const,
            yAxisIndex: 1,
            data: (props.barData ?? []).map((v, i) => ({
              value: v,
              itemStyle:
                monthFromLabel(props.categories[i] ?? '') === props.selectedMonth
                  ? { color: props.barColor ?? '#E7E6EE', borderColor: EMPHASIS_COLOR, borderWidth: 2 }
                  : { color: props.barColor ?? '#E7E6EE' },
            })),
            label: {
              show: true,
              position: 'insideTop' as const,
              color: props.barLabelColor ?? '#5C596E',
              formatter: barLabel,
            },
          },
        ]
      : []),
    ...props.lines.map((line) => ({
      name: line.name,
      type: 'line' as const,
      yAxisIndex: 0,
      data: line.data,
      itemStyle: { color: line.color },
      lineStyle: { color: line.color, width: 3, type: line.lineType ?? ('solid' as const) },
      // symbol: 'none'을 쓰면 ECharts가 해당 라인의 라벨까지 함께 숨기므로, 마커만 지우고
      // 라벨 앵커는 유지하기 위해 symbolSize를 0으로 낮추는 방식을 쓴다.
      symbol: 'circle' as const,
      symbolSize: line.showSymbol === false ? 0 : 8,
      label: {
        show: true,
        position: line.labelPosition ?? 'top',
        color: line.color,
        formatter: (p: DefaultLabelFormatterCallbackParams) => lineLabel(line, p),
      },
    })),
  ],
}))
</script>
