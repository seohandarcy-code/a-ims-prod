import { computed, ref } from 'vue'
import {
  changePassword as changePasswordRequest,
  login as loginRequest,
  logout as logoutRequest,
} from '../api/client'

// 토큰은 메모리에만 보관한다 - 새로고침하거나 팝업을 다시 열면 로그아웃된다.
// (localStorage/sessionStorage에 저장하지 않기로 확정됨). sso 모드에서 새로고침해도
// 매번 로그인 버튼을 누르지 않아도 되는 건 이 원칙을 깨는 게 아니라, App.vue가
// prompt=none으로 IdP(Keycloak/사내 SSO) 자체의 세션을 다시 물어보는 방식으로
// 해결한다 — 우리 쪽엔 아무것도 영속화하지 않는다.
const token = ref<string | null>(null)
const role = ref<'admin' | 'user' | null>(null)
const userName = ref<string | null>(null)
const userTeam = ref<string | null>(null)
// 조용한 재인증(prompt=none)이 "IdP에 세션 없음"으로 끝났다는 신호 — 이때만 수동
// "회사 계정으로 로그인" 게이트를 보여준다(콜백이 계속 자동 재시도하면 리다이렉트
// 루프가 되므로, 이 값이 true인 동안은 App.vue가 조용한 시도를 다시 걸지 않는다).
const ssoRequired = ref(false)
// IdP 인증에는 성공했지만 allowed_users에 등록되지 않은 계정 — 관리자가 "접근
// 권한 관리" 탭에서 등록해줘야 한다. sso_required와 마찬가지로 재시도하지 않는다.
const accessDenied = ref(false)
// 브로커 자체와 통신이 안 되는 이상 상황(discovery/token/JWKS 네트워크 실패
// 등, app/api/auth.py의 broker_unreachable) — 단순히 IdP 세션이 없는 정상
// 상황(sso_required)과 구분해 게이트 화면에 에러 배너로 보여준다.
const ssoError = ref<string | null>(null)
const modalOpen = ref(false)
const authLoading = ref(false)
const authError = ref<string | null>(null)

// 관리자 편집이 성공할 때마다 증가한다. 대시보드 쪽 composable들이 이 값을
// watch 의존성에 포함시켜 편집 즉시 데이터를 다시 불러오도록 한다.
const dataVersion = ref(0)

const isAuthed = computed(() => token.value !== null)
const isAdmin = computed(() => role.value === 'admin')

// SSO 콜백(app/api/auth.py의 /sso/callback)이 로그인 성공 후
// "/#token=...&expires_in=...&role=..." 형태로, 조용한 재인증(prompt=none)이 IdP
// 세션 없음으로 끝나면 "/#sso_required=1" 형태로 리다이렉트해준다. 앱 부팅 시 1회
// 호출해 그 값을 메모리 상태로 옮기고 URL에서는 지운다 — "토큰은 메모리에만,
// 새로고침하면 로그아웃"이라는 기존 원칙을 그대로 지킨다(localStorage 등으로
// 영속화하는 게 아니라, 리다이렉트가 막 돌아온 이번 1회 로드에서만 채워 넣는
// 것이므로 원칙과 충돌하지 않는다). App.vue의 onMounted에서 호출한다.
function consumeSsoCallbackToken(): void {
  if (!window.location.hash) return

  const params = new URLSearchParams(window.location.hash.slice(1))

  // sso_error는 sso_required=1과 함께 올 수 있어(silent 실패) 아래 return문들과
  // 별개로 먼저 읽어둔다.
  if (params.has('sso_error')) {
    ssoError.value = params.get('sso_error')
  }

  if (params.has('sso_required')) {
    ssoRequired.value = true
    history.replaceState(null, '', window.location.pathname + window.location.search)
    return
  }

  if (params.has('access_denied')) {
    accessDenied.value = true
    history.replaceState(null, '', window.location.pathname + window.location.search)
    return
  }

  const ssoToken = params.get('token')
  if (ssoToken) {
    token.value = ssoToken
    role.value = params.get('role') === 'admin' ? 'admin' : 'user'
    userName.value = params.get('name')
    userTeam.value = params.get('team')
  }

  history.replaceState(null, '', window.location.pathname + window.location.search)
}

async function login(username: string, password: string): Promise<boolean> {
  authLoading.value = true
  authError.value = null

  try {
    const res = await loginRequest({ username, password })
    token.value = res.token
    role.value = res.role === 'admin' ? 'admin' : 'user'
    return true
  } catch (err) {
    authError.value = err instanceof Error ? err.message : String(err)
    return false
  } finally {
    authLoading.value = false
  }
}

async function logout(): Promise<void> {
  if (token.value) {
    try {
      await logoutRequest(token.value)
    } catch {
      // 서버 측 세션 정리에 실패해도 클라이언트 쪽 로그인 상태는 그대로 해제한다.
    }
  }
  token.value = null
  role.value = null
  userName.value = null
  userTeam.value = null
}

async function changePassword(currentPassword: string, newPassword: string): Promise<boolean> {
  if (!token.value) return false
  authLoading.value = true
  authError.value = null

  try {
    await changePasswordRequest(
      { current_password: currentPassword, new_password: newPassword },
      token.value,
    )
    return true
  } catch (err) {
    authError.value = err instanceof Error ? err.message : String(err)
    return false
  } finally {
    authLoading.value = false
  }
}

function bumpDataVersion(): void {
  dataVersion.value += 1
}

export function useAdminAuth() {
  return {
    token,
    role,
    userName,
    userTeam,
    isAuthed,
    isAdmin,
    ssoRequired,
    accessDenied,
    ssoError,
    modalOpen,
    authLoading,
    authError,
    dataVersion,
    login,
    logout,
    changePassword,
    bumpDataVersion,
    consumeSsoCallbackToken,
  }
}
