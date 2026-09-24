<template>
  <div class="page">
    <header class="page-header">
      <div class="page-header-main">
        <p class="small-title">
          {{ meta?.team_name ?? '인프라AX/PI팀' }}
        </p>
        <h1 class="big-title">
          {{ meta?.dashboard_title ?? "Investment Management Dashboard '26" }}
        </h1>
        <p
          v-if="meta"
          class="desc"
        >
          투자 계획, 심의, 계약, 완료 현황을 확인합니다.
        </p>
      </div>

      <div
        v-if="showUserBadge"
        class="current-user-badge"
      >
        <span class="current-user-team">{{ userTeam || '팀 미지정' }}</span>
        <span class="current-user-name">{{ userName }}</span>
        <span
          v-if="isAdmin"
          class="current-user-admin-tag"
        >관리자</span>
      </div>
    </header>

    <div
      v-if="canShowDashboard"
      class="page-body"
    >
      <SidebarFilters v-model:open="sidebarOpen" />

      <main class="main-content">
        <nav class="tab-bar">
          <button
            v-for="tab in visibleTabs"
            :key="tab.key"
            type="button"
            class="tab-btn"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </nav>

        <DashboardView v-if="activeTab === 'dashboard'" />
        <StatusDetailView v-else />
      </main>
    </div>

    <div
      v-else-if="accessDenied"
      class="login-gate"
    >
      <p class="login-gate-desc">
        등록되지 않은 계정입니다. 관리자에게 접근 권한 등록을 요청하세요.
      </p>
    </div>

    <div
      v-else-if="showLoginGate"
      class="login-gate"
    >
      <p class="login-gate-desc">
        이 대시보드는 회사 계정으로 로그인해야 볼 수 있습니다.
      </p>
      <p
        v-if="ssoError"
        class="sso-error-banner"
      >
        {{ ssoErrorMessage }}
      </p>
      <button
        type="button"
        class="login-gate-btn"
        @click="goToInteractiveLogin"
      >
        회사 계정으로 로그인
      </button>

      <form
        v-if="ssoAllowLocalLogin"
        class="local-fallback-form"
        @submit.prevent="handleLocalFallbackLogin"
      >
        <p class="local-fallback-desc">
          브로커 연동 전 임시 — 관리자 비밀번호로 로그인
        </p>
        <input
          v-model="fallbackUsername"
          type="text"
          placeholder="아이디"
          autocomplete="username"
        >
        <input
          v-model="fallbackPassword"
          type="password"
          placeholder="비밀번호"
          autocomplete="current-password"
        >
        <p
          v-if="authError"
          class="local-fallback-error"
        >
          {{ authError }}
        </p>
        <button
          type="submit"
          class="local-fallback-btn"
          :disabled="authLoading"
        >
          {{ authLoading ? '로그인 중...' : '관리자 비밀번호로 로그인' }}
        </button>
      </form>
    </div>

    <div
      v-else
      class="login-gate"
    >
      <p class="login-gate-desc">
        로그인 확인 중...
      </p>
    </div>

    <AdminModal v-if="canShowDashboard" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchAuthMode, SSO_LOGIN_URL, SSO_SILENT_LOGIN_URL } from './api/client'
import { useFilters } from './composables/useFilters'
import { useAdminAuth } from './composables/useAdminAuth'
import AdminModal from './components/admin/AdminModal.vue'
import SidebarFilters from './components/layout/SidebarFilters.vue'
import DashboardView from './views/DashboardView.vue'
import StatusDetailView from './views/StatusDetailView.vue'

const { meta, loadMeta } = useFilters()
const {
  token,
  isAuthed,
  isAdmin,
  userName,
  userTeam,
  ssoRequired,
  accessDenied,
  ssoError,
  authLoading,
  authError,
  login,
  consumeSsoCallbackToken,
} = useAdminAuth()

// 투자 진행 상세현황 탭은 2026-08-11 오너 요청으로 숨김 처리한다 — 코드/라우팅(?tab=status-detail)은
// 그대로 두고 탭 바에서만 감춘다(추후 재노출 시 hidden만 제거하면 됨).
const tabs = [
  { key: 'dashboard', label: '투자 종합현황', hidden: false },
  { key: 'status-detail', label: '투자 진행 상세현황', hidden: true },
] as const

const visibleTabs = computed(() => tabs.filter((t) => !t.hidden))

const initialTab = new URLSearchParams(window.location.search).get('tab')
const activeTab = ref<(typeof tabs)[number]['key']>(
  tabs.some((t) => t.key === initialTab) ? (initialTab as (typeof tabs)[number]['key']) : 'dashboard',
)

const sidebarOpen = ref(false)

// null = 아직 /auth/mode 응답을 못 받음(부팅 초기). local이면 지금까지처럼 대시보드가
// 항상 공개고, sso면 로그인 세션이 있어야만 대시보드를 그릴 수 있다.
const authMode = ref<'local' | 'sso' | null>(null)
// AUTH_MODE=sso에서도 브로커 client_id 발급 전 부트스트랩용으로 기존 로컬
// 비밀번호 로그인을 같이 열어둘지(app/config.py의 SSO_ALLOW_LOCAL_LOGIN).
const ssoAllowLocalLogin = ref(false)
// 브로커 client_id 등이 아직 설정 안 돼 있으면(app/auth/oidc.py의
// SSO_BROKER_CONFIGURED) oauth.sso 자체가 없어 /sso/login이 죽는다 — 이 값이
// false면 조용한 재인증 시도 자체를 걸지 않는다(아래 onMounted).
const ssoBrokerConfigured = ref(false)
const fallbackUsername = ref('admin')
const fallbackPassword = ref('')

const canShowDashboard = computed(() => authMode.value === 'local' || (authMode.value === 'sso' && isAuthed.value))
// sso 모드에서 조용한 재인증(prompt=none)이 이미 "IdP 세션 없음"으로 끝났거나
// (ssoRequired), 애초에 브로커가 설정 안 돼 있어 시도할 필요가 없었으면
// (!ssoBrokerConfigured) 수동 로그인 게이트를 보여준다 — 그 전(첫 로드, 아직
// 시도 전)에는 "확인 중" 문구만 보여주고 곧바로 조용한 시도를 건다(아래 onMounted).
const showLoginGate = computed(
  () =>
    authMode.value === 'sso' &&
    !isAuthed.value &&
    (ssoRequired.value || !ssoBrokerConfigured.value || !!ssoError.value) &&
    !accessDenied.value,
)

// SSO 실패 사유(app/api/auth.py의 sso_error)를 사람이 읽을 문구로 바꾼다.
// 지금은 broker_unreachable 하나뿐이지만 나중에 늘어날 걸 고려해 매핑으로 둔다.
const SSO_ERROR_MESSAGES: Record<string, string> = {
  broker_unreachable: 'SSO 브로커에 연결하지 못했습니다. 네트워크 또는 SSO_ISSUER_URL 설정을 확인해주세요.',
}
const ssoErrorMessage = computed(
  () => (ssoError.value && SSO_ERROR_MESSAGES[ssoError.value]) || 'SSO 로그인 중 오류가 발생했습니다.',
)
// 로그인은 됐지만(팀/이름을 아는) sso 모드일 때만 우측 상단 접속자 정보를 보여준다.
// local 모드는 개인별 계정 개념이 없어 표시할 게 없다.
// 로컬 비밀번호 폴백 로그인(SSO_ALLOW_LOCAL_LOGIN)은 userName을 안 채우므로,
// 실제 SSO로 들어온 세션에서만 배지를 보여준다(둘 다 "관리자"로 보이면 헷갈림).
const showUserBadge = computed(() => authMode.value === 'sso' && canShowDashboard.value && !!userName.value)

function goToInteractiveLogin(): void {
  window.location.href = SSO_LOGIN_URL
}

async function handleLocalFallbackLogin(): Promise<void> {
  const ok = await login(fallbackUsername.value, fallbackPassword.value)
  if (ok) {
    fallbackPassword.value = ''
    await loadMeta(token.value ?? undefined)
  }
}

onMounted(async () => {
  consumeSsoCallbackToken()

  const modeRes = await fetchAuthMode()
  authMode.value = modeRes.auth_mode
  ssoAllowLocalLogin.value = modeRes.sso_allow_local_login
  ssoBrokerConfigured.value = modeRes.sso_broker_configured

  if (authMode.value !== 'sso') {
    await loadMeta()
    return
  }

  if (token.value) {
    await loadMeta(token.value)
    return
  }

  if (ssoRequired.value || accessDenied.value || ssoError.value) {
    // 조용한 시도가 이미 실패로 끝났거나(ssoRequired) 미등록 계정으로 거부된
    // 상태(accessDenied) — 둘 다 재시도하지 않는다(자동 재시도하면 리다이렉트
    // 루프가 되거나, 매번 같은 거부 화면으로 왕복만 반복하게 된다). 브로커
    // 통신 실패(ssoError)도 마찬가지다 — non-silent 실패는 sso_required가
    // 안 딸려오므로 이 가드가 없으면 곧바로 또 조용한 시도를 걸어버린다.
    return
  }

  if (!ssoBrokerConfigured.value) {
    // 브로커 client_id 등이 아직 없으면 조용한 시도 자체가 무조건 실패(서버
    // 에러)하므로 아예 시도하지 않고 바로 게이트를 보여준다 — SSO_ALLOW_LOCAL_LOGIN이
    // 켜져 있으면 여기서 로컬 로그인 폼을 바로 볼 수 있다.
    return
  }

  // 첫 로드: 사내 다른 페이지 등에서 이미 SSO 로그인돼 있으면 버튼 없이 곧바로
  // 이어지도록 조용한 재인증을 1회 시도한다. IdP 세션이 없으면 콜백이
  // "#sso_required=1"로 돌아와 다음 로드에서 위 분기로 수동 게이트가 뜬다.
  window.location.href = SSO_SILENT_LOGIN_URL
})
</script>

<style scoped>
.page {
  max-width: 1660px;
  margin: 0 auto;
  padding: 2rem 2rem 3rem;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.page-header-main {
  min-width: 0;
}

.current-user-badge {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 0.9rem;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  background: var(--card-bg, #fff);
  font-size: 0.85rem;
  white-space: nowrap;
}

.current-user-team {
  color: var(--text-subtle);
}

.current-user-name {
  font-weight: 700;
  color: var(--text-main);
}

.current-user-admin-tag {
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: var(--select-fill);
  color: var(--select-fill-text);
  font-size: 0.72rem;
  font-weight: 700;
}

.page-body {
  /*
    SidebarFilters는 이제 FAB + fixed 오버레이 드로어 구조라 문서 흐름에 컬럼을
    예약할 필요가 없다. 기존 flex 레이아웃(사이드바 컬럼 + 본문 컬럼)을 단순 블록으로
    정리해 .main-content가 항상 전체 폭을 사용하도록 한다.
  */
  display: block;
}

.main-content {
  min-width: 0;
}

.tab-bar {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 1.2rem;
}

.tab-btn {
  /* 투자 진행 상세현황 탭을 숨기면서 남은 "투자 종합현황" 탭이 사실상 페이지 제목 역할을
     겸하게 되어 명칭/버튼 크기를 살짝 키웠다(2026-08-11 오너 요청). */
  padding: 0.8rem 1.6rem;
  border: none;
  border-radius: 999px;
  background: none;
  font-size: 1.15rem;
  font-weight: 650;
  color: var(--text-subtle);
  cursor: pointer;
}

.tab-btn.active {
  color: var(--neutral-strong);
  background: var(--neutral-soft);
  font-weight: 750;
}

.login-gate {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.2rem;
  padding: 5rem 1.5rem;
  text-align: center;
}

.login-gate-desc {
  color: var(--text-subtle);
  font-size: 1.05rem;
}

.sso-error-banner {
  width: 100%;
  max-width: 360px;
  margin: 0;
  padding: 0.65rem 0.9rem;
  border: 1px solid var(--border-color);
  border-left: 8px solid var(--tone-bad-border);
  border-radius: 0.6rem;
  background: var(--card-bg);
  color: var(--tone-bad-border);
  font-size: 0.85rem;
  line-height: 1.4;
  text-align: left;
}

.login-gate-btn {
  padding: 0.9rem 1.8rem;
  border: none;
  border-radius: 999px;
  background: var(--select-fill);
  color: var(--select-fill-text);
  font-size: 1.05rem;
  font-weight: 700;
  cursor: pointer;
}

.local-fallback-form {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding-top: 1.2rem;
  border-top: 1px dashed var(--border-color);
  width: 100%;
  max-width: 260px;
}

.local-fallback-desc {
  font-size: 0.8rem;
  color: var(--text-subtle);
  margin: 0 0 0.2rem;
}

.local-fallback-form input {
  width: 100%;
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  font-size: 0.9rem;
  box-sizing: border-box;
}

.local-fallback-error {
  font-size: 0.78rem;
  color: var(--tone-bad-border);
  margin: 0;
}

.local-fallback-btn {
  width: 100%;
  padding: 0.55rem 0;
  border: none;
  border-radius: 0.5rem;
  background: var(--neutral-soft);
  color: var(--text-main);
  font-weight: 700;
  cursor: pointer;
}

.local-fallback-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
