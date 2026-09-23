export interface FilterOptions {
  org: string[]
  leader_opinion: string[]
  center_need: string[]
  team: string[]
  part: string[]
}

/** 팀 → PJT → 파트 3단계 트리 노드. 파트 노드의 key는 "PJT::파트" 복합키. */
export interface OrgTreeNode {
  level: 'team' | 'pjt' | 'part'
  key: string
  label: string
  children?: OrgTreeNode[]
}

/** 사이드바 "투자 진행 흐름 구분" 필터 옵션 — 종합현황 퍼널과 동일한 key/label. */
export interface FlowStageOption {
  key: string
  label: string
}

export interface MetaResponse {
  current_month: number
  current_label: string
  team_name: string
  dashboard_title: string
  filter_options: FilterOptions
  org_options: string[]
  org_tree: OrgTreeNode[]
  flow_stage_options: FlowStageOption[]
  /** "local"(아이디/비밀번호) 또는 "sso"(OIDC 리다이렉트) — 로그인 UI 분기 근거. */
  auth_mode: 'local' | 'sso'
}

export interface DetailColumn {
  key: string
  label: string
  type: 'text' | 'number' | 'money' | 'progress'
}

export interface ExecutiveKpi {
  total_count: number
  invest_sum: number
  progress_count: number
  progress_sum: number
  review_count: number
  review_sum: number
  contract_done_count: number
  contract_done_sum: number
  investment_done_count: number
  investment_done_sum: number
  amount_execution_rate: number
  execution_settled_sum: number
}

/** "종합진행 퍼널"의 막대 하나. checkpoint(전체/진행/심의/계약/투자 완료) 또는
 * component(그 사이를 구성하는 세부 항목). group으로 색 계열(plan/review/contract/settle)을 정한다. */
export interface ProgressFunnelItem {
  key: string
  label: string
  count: number
  kind: 'checkpoint' | 'component'
  group: 'plan' | 'review' | 'contract' | 'settle'
}

export interface DashboardResponse {
  selected_org: string
  org_options: string[]
  executive_kpi: ExecutiveKpi
  progress_funnel: ProgressFunnelItem[]
  monthly_flow: Record<string, unknown>[]
  detail_columns: DetailColumn[]
  detail_search_keys: string[]
  detail_rows: Record<string, unknown>[]
}

/** 3단계(심의/계약/집행) 요약 — 종합현황 KPI와 동일한 판정 함수/분모를 사용한다. */
export interface StageSummary {
  total_count: number
  review_done_count: number
  review_completion_rate: number
  review_pending_count: number
  investment_done_count: number
  contract_count: number
  review_to_contract_rate: number
  execution_po_sum: number
  executed_sum: number
  amount_execution_rate: number
  contract_backlog_count: number
}

export interface OrgReviewCompletionRow {
  org: string
  completed: number
  incomplete: number
  total: number
}

export interface OrgContractRow {
  org: string
  registered: number
  unregistered: number
  total: number
}

export interface OrgExecutionRow {
  org: string
  count: number
  invest_cost: number
  execution_po_amount: number
  executed_amount: number
  unexecuted_amount: number
  execution_rate: number
}

export interface MonitoringBlock<TOrgRow> {
  summary: StageSummary
  org_table: TOrgRow[]
  monthly_table: Record<string, unknown>[]
}

export interface StatusDetailResponse {
  review_monitoring: MonitoringBlock<OrgReviewCompletionRow>
  contract_monitoring: MonitoringBlock<OrgContractRow>
  execution_monitoring: MonitoringBlock<OrgExecutionRow>
}

export interface CommonFilterParams {
  org?: string[]
  leader_opinion?: string[]
  center_need?: string[]
  team?: string[]
  part?: string[]
  /** 사이드바 "투자 진행 흐름 구분" 다중선택 필터 — 선택된 key들을 OR로 합쳐서 적용한다. */
  flow_stage?: string[]
  selected_org?: string
  /** 종합진행 퍼널 막대 클릭 필터(대시보드 전용) — status-detail 등 다른 화면에서는 항상 미설정. */
  funnel_key?: string
  /** 월별 진행 흐름 그래프 클릭 필터(대시보드 전용, 계약월_입력 기준) — status-detail 등에서는 항상 미설정. */
  month_key?: number
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  token: string
  token_type: string
  expires_in: number
  role: string
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

export interface StatusResponse {
  status: string
}

export interface AdminRowColumn {
  key: string
  label: string
  type: 'text' | 'money' | 'month' | 'date' | 'month_list' | 'money_list' | 'status'
  placeholder?: string | null
  deletable: boolean
}

export type AdminRawRow = Record<string, string>

export interface RawDataResponse {
  columns: AdminRowColumn[]
  rows: AdminRawRow[]
  has_backup: boolean
}

export interface RowEditRequest {
  fields: Record<string, string>
}

export interface RowResponse {
  row: AdminRawRow
}

export interface AddColumnRequest {
  name: string
  type?: 'text' | 'money' | 'date'
}

export interface AllowedUser {
  sso_id: string
  name: string
  team: string
  is_admin: boolean
}

export interface AllowedUserCreateRequest {
  sso_id: string
  name: string
  team: string
  is_admin: boolean
}

export interface AllowedUserUpdateRequest {
  name: string
  team: string
  is_admin: boolean
}
