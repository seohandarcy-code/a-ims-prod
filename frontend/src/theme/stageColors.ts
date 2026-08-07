/**
 * 단계 색상 언어(심의=블루/계약=퍼플/집행=그린) 상수 모듈 — 3단 티어(ink/fill/wash).
 * ECharts option은 순수 JS 객체라 CSS 변수를 읽지 못하므로, theme/tokens.css의
 * --stage-*-{ink,fill,wash} 값과 반드시 동일하게 유지할 것.
 * po/contract/execution = ink 티어, *Soft = wash 티어(하위호환 이름 유지), *Fill = fill 티어.
 * 파스텔 톤 전환(2026-08-07) — 근거는 docs/design-review/2026-08-07-pastel-palette-review.md 참고.
 */
export const STAGE = {
  po: '#3B5BC0',
  contract: '#7A5BC4',
  execution: '#1E8264',
  poFill: '#7189DC',
  contractFill: '#9E80DB',
  executionFill: '#3DA07E',
  poSoft: '#E6EAFA',
  contractSoft: '#EFEAFB',
  executionSoft: '#DCF0E8',
} as const

/**
 * 다크(프레젠테이션 모드) 진한 색 3종.
 * 다음 라운드에서 프레젠테이션 모드(`/present`) 도입 시 사용 예정 — 현재는 어디서도 참조되지 않음.
 * theme/tokens.css의 `:root[data-theme="dark"]` 블록 값과 반드시 동일하게 유지할 것.
 */
export const STAGE_DARK = {
  po: '#60A5FA',
  contract: '#A78BFA',
  execution: '#34D399',
} as const

export type StageKey = 'po' | 'contract' | 'execution'

const STAGE_NAME_MAP: Record<string, StageKey> = {
  품의완료: 'po',
  계약등록: 'contract',
  집행발생: 'execution',
}

const NEUTRAL_COLOR = 'var(--neutral-strong)'

export function stageColorByName(stage: string): string {
  const key = STAGE_NAME_MAP[stage]
  if (!key) return NEUTRAL_COLOR
  return STAGE[key]
}

/**
 * 진단(병목) 단계 이름 -> 단계색 매핑. STAGE_NAME_MAP(완료형: 품의완료/계약등록/집행발생)과는
 * 의미가 반대(병목형: 품의 지연/계약 대기/집행 대기/잔여 집행)라 별도로 둔다.
 * 집행 대기·잔여 집행은 둘 다 execution(그린)으로 통일한다(오너 확정 사항, 2026-07-21).
 */
const DIAGNOSIS_STAGE_MAP: Record<string, StageKey> = {
  '품의 지연': 'po',
  '계약 대기': 'contract',
  '집행 대기': 'execution',
  '잔여 집행': 'execution',
}

export function diagnosisStageKey(stage: string): StageKey | null {
  return DIAGNOSIS_STAGE_MAP[stage] ?? null
}
