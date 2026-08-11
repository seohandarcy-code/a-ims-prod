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

/** 카테고리 값(월별 데이터)과 무관하게 그리드 전체 폭을 가로지르는 수평 기준선. 데이터
 * 포인트 배열이 아니라 markLine으로 그려서, 마지막 카테고리(예: 12월)의 "중심"이 아니라
 * 축의 끝(마디) 끝까지 선이 이어지고 그 뒤에 값 라벨이 붙는다(2026-08-11 오너 요청). */
export interface ReferenceLine {
  value: number
  color: string
  formatter?: (value: number) => string
  /** 범례에 표시할 이름. 지정하면 범례에 배지가 뜨고(2026-08-11 오너 요청 — markLine 전환
   * 이후 사라졌던 범례 항목 복원), 지정하지 않으면 범례 없이 선만 그린다. */
  name?: string
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
  referenceLine?: ReferenceLine
}>()

const emit = defineEmits<{ select: [month: number] }>()

const EMPHASIS_COLOR = '#595870'
const FUTURE_SHADE_COLOR = 'rgba(141, 142, 164, 0.08)'
const SELECTED_MONTH_SHADE_COLOR = 'rgba(59, 91, 192, 0.10)'

const hasBar = computed(() => !!props.barName && !!props.barData && props.barData.length > 0)

// 데이터가 아직 없는 "미래" 구간을 옅게 음영 처리하기 위한 기준월 인덱스 — 기준선처럼 12월까지
// 값이 꽉 차 있는 라인(labelOnlyLast)은 제외하고, 실제 월별 데이터 라인 중 값이 있는 마지막
// 인덱스를 찾는다(2026-08-11 오너 요청 — 격자 정리 + 미래구간 음영 + 선택월 하이라이트,
// 매월 누적값 라벨은 그대로 유지).
const lastDataIndex = computed(() => {
  let last = -1
  for (const line of props.lines) {
    if (line.labelOnlyLast) continue
    for (let i = line.data.length - 1; i >= 0; i--) {
      if (line.data[i] !== null && line.data[i] !== undefined) {
        last = Math.max(last, i)
        break
      }
    }
  }
  return last
})

// 미래(데이터 없는) 구간 음영 — 서로 다른 카테고리 문자열 두 개를 좌/우 경계로 주면 ECharts가
// 그 두 카테고리를 포함한 "칸 전체"를 채운다. 단, 이 edge-to-edge 해석은 같은 x축을 쓰는 bar
// 시리즈가 하나라도 있어야 성립한다 — bar가 전혀 없으면(예: 대시보드에서 월 선택을 안 한 상태,
// 라인만 있는 상태) ECharts가 카테고리 좌표를 밴드 경계가 아니라 "점(중심)" 기준으로 해석해
// 좌우 반 칸씩 짧게 그려진다(2026-08-11 실측 확인 — 막대 상세현황 서브탭·선택월 있는 대시보드는
// 이미 막대가 있어 정상, 선택 없는 대시보드에서만 재현). subtabs(hasBar=true)는 실제 막대
// 시리즈가 항상 있어 이 markArea 방식이 안전하게 동작하므로 그대로 둔다.
const futureShadeArea = computed(() => {
  const futureFrom = lastDataIndex.value + 1
  if (lastDataIndex.value < 0 || futureFrom >= props.categories.length) return null
  return [
    { xAxis: props.categories[futureFrom], itemStyle: { color: FUTURE_SHADE_COLOR } },
    { xAxis: props.categories[props.categories.length - 1] },
  ]
})

const selectedMonthIndex = computed(() => {
  if (props.selectedMonth == null) return -1
  return props.categories.indexOf(`${props.selectedMonth}월`)
})

// hasBar=false(대시보드)에서는 markArea가 기댈 bar 시리즈가 없을 수 있어(선택월 미지정 시)
// 위 markArea 방식을 아예 쓰지 않는다. 대신 숨겨진 0~1 보조축 위에 카테고리별 값 0/1인 배경
// 막대 시리즈를 깔아 미래구간 음영과 선택월 하이라이트를 함께 그린다 — 막대는 밴드 유무와
// 무관하게 항상 자기 카테고리 칸 전체(barWidth:'100%')를 정확히 채우므로 이 문제 자체가
// 생기지 않는다(2026-08-11).
const backgroundBarData = computed(() => {
  if (hasBar.value) return null
  const futureFrom = lastDataIndex.value
  return props.categories.map((_, i) => {
    if (i === selectedMonthIndex.value) return { value: 1, itemStyle: { color: SELECTED_MONTH_SHADE_COLOR } }
    if (futureFrom >= 0 && i > futureFrom) return { value: 1, itemStyle: { color: FUTURE_SHADE_COLOR } }
    return { value: 0 }
  })
})

// markLine으로 그리는 기준선은 series data가 아니라서 ECharts의 y축 자동 스케일 계산에
// 잡히지 않는다 — 그대로 두면 기준선 값이 실제 데이터 최댓값보다 클 때 축 범위 밖(그래프
// 위쪽 바깥)에 그려져 안 보인다. 기준선 값까지 포함해 축 최댓값을 직접 계산한다.
const leftAxisMax = computed(() => {
  if (!props.referenceLine) return undefined
  let dataMax = 0
  for (const line of props.lines) {
    for (const v of line.data) {
      if (v !== null && v !== undefined && v > dataMax) dataMax = v
    }
  }
  const target = Math.max(dataMax, props.referenceLine.value)
  return Math.ceil((target * 1.12) / 10) * 10
})

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

const AXIS_SPLIT_LINE_COLOR = '#E7E6EE'

const option = computed<EChartsOption>(() => {
  // 격자 정리 + 미래구간 음영 + 선택월 하이라이트(2026-08-11 오너 요청) — 매월 누적값 라벨은
  // 그대로 두고, 배경 요소(격자선/음영)만 정리한다.
  const seriesList: Record<string, unknown>[] = []

  // 미래구간 음영 + 선택월 하이라이트 배경 막대를 다른 시리즈보다 먼저 넣어(렌더 순서상 가장
  // 아래) 라인/막대에 가려지지 않으면서도 그 위로 그려지는 다른 시리즈에 배경처럼 깔리게 한다.
  // hasBar=true(상세현황 서브탭)에서는 실제 막대 시리즈가 항상 있어 markArea가 안전하게
  // 동작하므로 이 배경 막대는 생략한다(막대 2개가 카테고리 폭을 나눠 갖는 정렬 문제도 함께
  // 피함) — 미래구간 음영은 아래 markArea 블록에서 처리한다.
  if (backgroundBarData.value) {
    seriesList.push({
      name: '__month_background__',
      type: 'bar' as const,
      yAxisIndex: 1,
      silent: true,
      barWidth: '100%',
      itemStyle: { color: 'transparent' },
      emphasis: { disabled: true },
      tooltip: { show: false },
      legendHoverLink: false,
      data: backgroundBarData.value,
    })
  }

  if (hasBar.value) {
    seriesList.push({
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
    })
  }

  seriesList.push(
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
  )

  // 미래구간 음영(markArea)은 hasBar=true일 때만 쓴다 — 이때는 seriesList[0]이 항상 실제 막대
  // 시리즈라 markArea의 카테고리 좌표가 밴드 경계로 정확히 해석된다. hasBar=false는 위 배경
  // 막대 시리즈가 미래구간 음영까지 함께 처리하므로 여기서는 건드리지 않는다.
  if (hasBar.value && seriesList.length > 0 && futureShadeArea.value) {
    seriesList[0].markArea = { silent: true, data: [futureShadeArea.value] }
  }

  // 기준선(referenceLine)은 카테고리 데이터 포인트가 아니라 markLine으로 그린다 — 데이터 배열
  // 기반 라인은 마지막 카테고리(예: 12월)의 "중심"까지만 이어지지만, markLine은 그리드 좌/우
  // 끝(마디)까지 꽉 채워서 그려지고 그 뒤에 라벨이 붙는다(2026-08-11 오너 요청). markLine의
  // yAxis 값은 그 값을 붙인 시리즈의 yAxisIndex 기준으로 해석되므로, 반드시 금액축(yAxisIndex:0)
  // 위에 있는 시리즈에 붙여야 한다.
  if (props.referenceLine) {
    const rl = props.referenceLine
    const markLine = {
      silent: true,
      symbol: 'none',
      // markLine 기본 애니메이션(좌→우로 선이 자라나는 진입 효과)이 켜져 있으면, 월 선택처럼
      // referenceLine 값과 무관한 이유로 option이 재계산될 때마다 매번 새 객체로 교체되면서
      // 매번 다시 그려지는 것처럼 보인다(2026-08-11 오너 피드백) — 값 자체가 안 바뀌는
      // 기준선이라 애니메이션이 필요 없으므로 꺼서 항상 고정된 상태로만 보이게 한다.
      animation: false,
      lineStyle: { color: rl.color, type: 'dashed' as const, width: 2 },
      label: {
        show: true,
        position: 'end' as const,
        color: rl.color,
        formatter: () => (rl.formatter ? rl.formatter(rl.value) : String(rl.value)),
      },
      data: [{ yAxis: rl.value }],
    }

    if (rl.name) {
      // 범례에 기준선 배지를 띄우려면 이름이 있는 시리즈가 필요하다 — data가 없는(빈 배열)
      // 라인을 하나 만들어 markLine만 이 시리즈에 달아서, 실제로는 markLine만 그려지고 이
      // "유령" 라인 자체는 아무 점도 그리지 않는다.
      seriesList.push({
        name: rl.name,
        type: 'line' as const,
        yAxisIndex: 0,
        data: [],
        showSymbol: false,
        symbol: 'none',
        silent: true,
        tooltip: { show: false },
        lineStyle: { color: rl.color, type: 'dashed' as const, width: 2 },
        itemStyle: { color: rl.color },
        markLine,
      })
    } else {
      const firstLineSeries = seriesList.find((s) => s.type === 'line')
      if (firstLineSeries) firstLineSeries.markLine = markLine
    }
  }

  return {
    // right는 'right' 위치 라벨(예: 기준선 라벨)이 잘리지 않을 최소한만 확보한다 —
    // 기존 95px은 필요 이상으로 넓어 좌우 여백이 어긋나 보였다(2026-08-10 오너 피드백).
    grid: { left: 55, right: 68, top: 55, bottom: 60 },
    // 미래구간/선택월 배경 막대(__month_background__)는 범례에 노출할 항목이 아니므로
    // 명시적으로 실데이터 시리즈 이름만 나열한다.
    legend: { top: 0, data: seriesList.filter((s) => s.name !== '__month_background__').map((s) => s.name as string) },
    xAxis: {
      type: 'category',
      // 각 월이 두 마디(눈금) 사이의 온전한 한 칸을 차지하도록 명시한다 — 음영/하이라이트를
      // 그 칸의 경계(마디)에 정확히 맞추기 위한 전제(2026-08-11 오너 요청).
      boundaryGap: true,
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
          {
            type: 'value',
            name: props.leftAxisName ?? '',
            position: 'left',
            max: leftAxisMax.value,
            splitNumber: 4,
            splitLine: { lineStyle: { type: 'dashed', color: AXIS_SPLIT_LINE_COLOR } },
          },
          { type: 'value', name: props.rightAxisName ?? '', position: 'right', splitLine: { show: false } },
        ]
      : [
          {
            type: 'value',
            name: props.leftAxisName ?? '',
            position: 'left',
            max: leftAxisMax.value,
            splitNumber: 4,
            splitLine: { lineStyle: { type: 'dashed', color: AXIS_SPLIT_LINE_COLOR } },
          },
          // 선택월 하이라이트 배경 막대 전용 숨은 보조축(0~1) — 화면에는 보이지 않고, 막대
          // 시리즈가 카테고리 칸 전체(barWidth:'100%')를 정확히 채우게 하는 용도로만 쓴다.
          { type: 'value', show: false, min: 0, max: 1 },
        ],
    series: seriesList,
  }
})
</script>
