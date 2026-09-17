import type {
  AddColumnRequest,
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

export function fetchMeta(): Promise<MetaResponse> {
  return getJson<MetaResponse>(`${API_BASE}/meta`)
}

export function fetchDashboard(params: CommonFilterParams): Promise<DashboardResponse> {
  return getJson<DashboardResponse>(`${API_BASE}/dashboard${buildQuery(params)}`)
}

export function fetchStatusDetail(params: CommonFilterParams): Promise<StatusDetailResponse> {
  return getJson<StatusDetailResponse>(`${API_BASE}/status-detail${buildQuery(params)}`)
}

export function login(payload: LoginRequest): Promise<LoginResponse> {
  return postJson<LoginResponse>(`${API_BASE}/auth/login`, payload)
}

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
