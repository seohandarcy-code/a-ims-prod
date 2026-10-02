# 사내 SSO 브로커가 제공한 파이썬 레퍼런스 예시 코드 — 실제로 우리 레포 코드가
# 아니다(router/settings/BROKER_URL 등은 정의돼 있지 않음, import 불가).
# 2026-10-02 실제 브로커 연동 중 이 코드를 근거로 discovery 없는
# implicit + form_post 흐름을 확인하고, backend/app/auth/oidc.py의
# build_broker_authorize_url()/verify_broker_id_token()과
# backend/app/api/auth.py의 /sso/login·/sso/callback(SSO_FLOW_MODE=implicit_form_post
# 분기)을 이 코드를 최대한 그대로 따라 구현했다 — 자세한 경위는
# docs/db-migration-roadmap.md 4단계의 해당 날짜 항목 참고.
#
# 오타(jwt.InvalidTokenError 등 일부 철자)도 원문 그대로 보존한다 — 근거 자료이므로
# 임의로 고치지 않는다.

# sso 로그인 시작
@router.get("/sso")
async def sso_login(request: Request):
    host = request.headers.get("host","")
    base_url = f"https://{host.strip().rstrip('/')}"
    redirect_uri = f"{base_url}/auth/callback"

    try:
        url = build_sso_url(redirect_uri)
    except ValueError as e:
        raise HTTPException(500, str(e))

    return RedirectResponse(url=url)

#sso 콜백
@router.post("/callback")
async def auth_callback(request: Request, Form_data: CallbackForm = Depends()):
    
    try:
        claims = extract_calims(form_data.id_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "인증 티켓이 만료되었습니다.")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "인증 토큰 검증 실패")
    except Exception as e:
        raise HTTPException(500, f"로그인 처리 오류: {e}")

loginid = claims.get("loginid","")
name = claims.get("username","")
...

@dataClass
class CallbackForm:
    id_token:str =Form(...)


#sso/adfs
def build_sso_url(redirect_uri:str) -> str :
    if BROKER_URL:
        return f"{BROKER_URL}/oidc/form-authorize?client_id={SERVICE_ID}&redirect_uri={redirect_uri}"

    if not settings.ADFS_CLIENT_ID:
        raise ValueError("ADFS_CLIENT_ID가 설정되지 않았습니다.")
    query_params = {
        "client_id": settings.ADFS_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_mode":"form_post",
        "response_type": "code id_token",
        "scope": "openid profile",
        "nonce": str(uuid.uuid4()),
    }
    return f"{settings.ADFS_URL}?{urlencode(query_params)}"


def extract_claims(id_token:str) -> dict:

    if BROKER_URL:

        jwks_url = f"{BROKER_URL}/oidc/jwks"
        response =requests.get(jwks_url, verify=False)
        response.raise_for_status()
        jwks = response.json()
        public_key = RSAAlgorithm.from_jwk(json.dumps(jwks["keys"][0]))

    else:

        cert_file = path(__file__).resolve().parent.parent / settings.ADFS_CERT_FILE
        with open(cert_file,'rb') as f:
            cert_str = f.read()

        cert_obj = x509.load_pem_x509_certificate(cert_str)
        public_key = cert_obj.public_key()

    return jwt.decode(
        jwt=id_token.encode(),
        key=public_key,
        algorithms=['RS256'], 
        options={"verify_signature": True, "verify_exp": True, "verify_aud": False},
    )


























