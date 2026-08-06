import { computed, ref } from 'vue'
import {
  changePassword as changePasswordRequest,
  login as loginRequest,
  logout as logoutRequest,
} from '../api/client'

// 토큰은 메모리에만 보관한다 - 새로고침하거나 팝업을 다시 열면 로그아웃된다.
// (localStorage/sessionStorage에 저장하지 않기로 확정됨)
const token = ref<string | null>(null)
const modalOpen = ref(false)
const authLoading = ref(false)
const authError = ref<string | null>(null)

// 관리자 편집이 성공할 때마다 증가한다. 대시보드 쪽 composable들이 이 값을
// watch 의존성에 포함시켜 편집 즉시 데이터를 다시 불러오도록 한다.
const dataVersion = ref(0)

const isAuthed = computed(() => token.value !== null)

async function login(username: string, password: string): Promise<boolean> {
  authLoading.value = true
  authError.value = null

  try {
    const res = await loginRequest({ username, password })
    token.value = res.token
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
    isAuthed,
    modalOpen,
    authLoading,
    authError,
    dataVersion,
    login,
    logout,
    changePassword,
    bumpDataVersion,
  }
}
