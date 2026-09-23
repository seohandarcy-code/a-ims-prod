import type {
  AddColumnRequest,
  AllowedUser,
  AllowedUserCreateRequest,
  AllowedUserUpdateRequest,
  ChangePasswordRequest,
  CommonFilterParams,
  DashboardResponse,
  LoginRequest,
  LoginResponse,
  MetaResponse,
  RawDataResponse,
  RowEditRequest,
  RowResponse,
  StatusDetailResponse,
  StatusResponse,
} from '../types/api'

const API_BASE = `${import.meta.env.VITE_API_BASE_URL ?? ''}/api/v1`

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function buildQuery(params: CommonFilterParams): string {
  const search = new URLSearchParams()

  const appendAll = (key: string, values?: string[]) => {
    if (values === undefined) return
    for (const v of values) search.append(key, v)
  }

  appendAll('org', params.org)
  appendAll('leader_opinion', params.leader_opinion)
  appendAll('center_need', params.center_need)
  appendAll('team', params.team)
  appendAll('part', params.part)
  appendAll('flow_stage', params.flow_stage)

  if (params.selected_org) search.set('selected_org', params.selected_org)
  if (params.funnel_key) search.set('funnel_key', params.funnel_key)
  if (params.month_key !== undefined) search.set('month_key', String(params.month_key))

  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)

  if (!res.ok) {
    let detail = ''
    try {
      const body = await res.json()
      detail = typeof body?.detail === 'string' ? body.detail : ''
    } catch {
      // 본문이 JSON이 아니면 무시하고 기본 메시지를 사용한다.
    }
    throw new ApiError(res.status, detail || `요청 실패 (${res.status}): ${url}`)
  }

  return (await res.json()) as T
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` }
}

function authedJson<T>(url: string, token: string): Promise<T> {
  return getJson<T>(url, { headers: authHeaders(token) })
}

function postJson<T>(url: string, body: unknown, token?: string): Promise<T> {
  return getJson<T>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? authHeaders(token) : {}),
    },
    body: JSON.stringify(body),
  })
}

function patchJson<T>(url: string, body: unknown, token: string): Promise<T> {
  return getJson<T>(url, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(token),
    },
    body: JSON.stringify(body),
  })
}

function deleteJson<T>(url: string, token: string): Promise<T> {
  return getJson<T>(url, { method: 'DELETE', headers: authHeaders(token) })
}

// AUTH_MODE=sso일 때 /meta·/dashboard·/status-detail은 require_viewer로 게이트돼
// 있어 토큰 없이는 401이 난다(local 모드는 서버가 no-op이라 토큰 없이 넘겨도 안전).
export function fetchMeta(token?: string): Promise<MetaResponse> {
  return getJson<MetaResponse>(`${API_BASE}/meta`, token ? { headers: authHeaders(token) } : undefined)
}

export function fetchDashboard(params: CommonFilterParams, token?: string): Promise<DashboardResponse> {
  return getJson<DashboardResponse>(
    `${API_BASE}/dashboard${buildQuery(params)}`,
    token ? { headers: authHeaders(token) } : undefined,
  )
}

export function fetchStatusDetail(params: CommonFilterParams, token?: string): Promise<StatusDetailResponse> {
  return getJson<StatusDetailResponse>(
    `${API_BASE}/status-detail${buildQuery(params)}`,
    token ? { headers: authHeaders(token) } : undefined,
  )
}

export function login(payload: LoginRequest): Promise<LoginResponse> {
  return postJson<LoginResponse>(`${API_BASE}/auth/login`, payload)
}

// 프론트가 로그인 여부를 판단하기 이전에 지금이 로그인 게이트가 필요한 모드인지부터
// 알아야 하는 완전 공개 엔드포인트(/meta는 sso 모드에서 게이트돼 있어 로그인 전에는
// 못 부른다).
export interface AuthModeInfo {
  auth_mode: 'local' | 'sso'
  sso_allow_local_login: boolean
  sso_broker_configured: boolean
}

export function fetchAuthMode(): Promise<AuthModeInfo> {
  return getJson<AuthModeInfo>(`${API_BASE}/auth/mode`)
}

// SSO 로그인은 fetch가 아니라 실제 페이지 이동으로 시작해야 한다(IdP 리다이렉트를
// 타야 하므로) — 그래서 함수가 아니라 이동할 URL 문자열만 내보낸다.
export const SSO_LOGIN_URL = `${API_BASE}/auth/sso/login`

// 사내에서 이미 SSO로 로그인돼 있으면(다른 사내 페이지 등) 버튼 클릭 없이 조용히
// 재인증하기 위한 prompt=none 시도용 URL. IdP 세션이 없으면 로그인 폼 대신
// login_required류 오류로 돌아오고, 백엔드가 그걸 "#sso_required=1"로 변환해준다.
export const SSO_SILENT_LOGIN_URL = `${API_BASE}/auth/sso/login?silent=1`

export function logout(token: string): Promise<StatusResponse> {
  return postJson<StatusResponse>(`${API_BASE}/auth/logout`, {}, token)
}

export function changePassword(payload: ChangePasswordRequest, token: string): Promise<StatusResponse> {
  return postJson<StatusResponse>(`${API_BASE}/auth/change-password`, payload, token)
}

export function fetchAdminRawData(token: string): Promise<RawDataResponse> {
  return authedJson<RawDataResponse>(`${API_BASE}/admin/raw-data`, token)
}

export function editAdminRow(no: number | string, payload: RowEditRequest, token: string): Promise<RowResponse> {
  return patchJson<RowResponse>(`${API_BASE}/admin/rows/${no}`, payload, token)
}

export function addAdminRow(payload: RowEditRequest, token: string): Promise<RowResponse> {
  return postJson<RowResponse>(`${API_BASE}/admin/rows`, payload, token)
}

export function deleteAdminRow(no: number | string, token: string): Promise<StatusResponse> {
  return deleteJson<StatusResponse>(`${API_BASE}/admin/rows/${no}`, token)
}

export function restoreAdminBackup(token: string): Promise<StatusResponse> {
  return postJson<StatusResponse>(`${API_BASE}/admin/rows/restore`, {}, token)
}

export function addAdminColumn(payload: AddColumnRequest, token: string): Promise<StatusResponse> {
  return postJson<StatusResponse>(`${API_BASE}/admin/columns`, payload, token)
}

export function deleteAdminColumn(key: string, token: string): Promise<StatusResponse> {
  return deleteJson<StatusResponse>(`${API_BASE}/admin/columns/${encodeURIComponent(key)}`, token)
}

export async function fetchAdminCsvBlob(token: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/admin/export/csv`, { headers: authHeaders(token) })
  if (!res.ok) {
    throw new ApiError(res.status, `CSV 다운로드 실패 (${res.status})`)
  }
  return res.blob()
}

// 운영 DB 백업 스냅샷(.dat) 다운로드 — 로컬 개발 환경을 이 파일로 재시딩할 때 쓴다
// (backend/scripts/reseed_from_dat.py --file <다운로드파일> --reset).
export async function fetchAdminDatBlob(token: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/admin/export/dat`, { headers: authHeaders(token) })
  if (!res.ok) {
    throw new ApiError(res.status, `dat 다운로드 실패 (${res.status})`)
  }
  return res.blob()
}

// SSO 로그인 접근 제어 목록("접근 권한 관리" 탭) — 누가 로그인할 수 있는지/누가
// admin인지 관리자가 직접 등록·수정·삭제한다.
export function fetchAccessUsers(token: string): Promise<AllowedUser[]> {
  return authedJson<AllowedUser[]>(`${API_BASE}/admin/access-users`, token)
}

export function createAccessUser(payload: AllowedUserCreateRequest, token: string): Promise<AllowedUser> {
  return postJson<AllowedUser>(`${API_BASE}/admin/access-users`, payload, token)
}

export function updateAccessUser(
  ssoId: string,
  payload: AllowedUserUpdateRequest,
  token: string,
): Promise<AllowedUser> {
  return patchJson<AllowedUser>(`${API_BASE}/admin/access-users/${encodeURIComponent(ssoId)}`, payload, token)
}

export function deleteAccessUser(ssoId: string, token: string): Promise<StatusResponse> {
  return deleteJson<StatusResponse>(`${API_BASE}/admin/access-users/${encodeURIComponent(ssoId)}`, token)
}
