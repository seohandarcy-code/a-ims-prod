# 사내 AD SSO 개발 환경 연동 가이드
## HTTP 개발 서버, SSO Broker, HTTPS/SSL 인증서의 역할 이해

> 목적: 사내 AD 기반 SSO 환경에서 개발 중인 HTTP 웹 애플리케이션을 SSO Broker를 통해 테스트할 때, HTTPS와 SSL/TLS 인증서가 어떤 역할을 하는지 이해하고 실제 웹 개발 시 참고할 수 있도록 정리한 문서입니다.

---

## 1. 핵심 개념

사내 AD SSO 환경에서는 보통 운영 웹 서비스가 HTTPS로 제공됩니다.

```text
https://service.company.com
```

반면 개발 단계에서는 애플리케이션을 다음처럼 HTTP로 실행하는 경우가 많습니다.

```text
http://dev-server:8080
http://localhost:3000
http://192.168.0.10:8080
```

이때 회사에서 별도의 **SSO Broker 서버**를 제공한다면, 일반적으로 Broker가 개발 애플리케이션 앞단에서 HTTPS와 SSO 인증을 담당하고, 내부의 HTTP 개발 서버로 요청을 전달하는 구조일 가능성이 높습니다.

대표 구조:

```text
[사용자 브라우저]
        |
        | HTTPS
        v
[SSO Broker / Reverse Proxy]
        |
        | AD SSO
        |
        | HTTP 또는 HTTPS
        v
[개발 Web Application]
```

중요한 점은 다음과 같습니다.

> SSL/TLS 인증서가 AD SSO 인증 자체를 수행하는 것은 아니다.

AD SSO와 SSL/TLS는 서로 다른 역할을 담당합니다.

---

## 2. 각 구성요소의 역할

| 구성요소 | 역할 |
|---|---|
| Active Directory | 사내 사용자 계정 및 인증 정보 관리 |
| SSO Broker | AD 인증과 웹 애플리케이션 사이의 중계 역할 |
| Kerberos / SAML / OIDC | 인증 정보를 전달하기 위한 프로토콜 |
| SSL/TLS 인증서 | 서버 신원 확인 및 통신 암호화 |
| HTTPS | HTTP 통신에 TLS 암호화를 적용한 방식 |
| Web Application | 실제 업무 서비스 또는 개발 중인 웹 애플리케이션 |

즉 다음과 같이 역할을 분리해서 이해하는 것이 좋습니다.

```text
AD
 └─ 누가 사용자인가?

SSO Broker
 └─ 인증을 웹 서비스와 어떻게 연결할 것인가?

OIDC / SAML / Kerberos
 └─ 인증 정보를 어떤 방식으로 전달할 것인가?

SSL/TLS
 └─ 네트워크 통신을 어떻게 보호할 것인가?

Web Application
 └─ 인증된 사용자를 이용하여 어떤 서비스를 제공할 것인가?
```

---

## 3. 운영 환경의 일반적인 구조

운영 환경에서는 일반적으로 모든 사용자 접근이 HTTPS로 이루어집니다.

```text
사용자
   |
   | HTTPS
   v
https://service.company.com
   |
   v
SSO / AD 인증
   |
   v
Web Application
```

HTTPS는 다음 정보를 보호합니다.

- 로그인 과정의 인증 정보
- 세션 쿠키
- Access Token
- ID Token
- 사용자 정보
- 업무 데이터
- API 요청 및 응답

따라서 운영 환경에서는 HTTPS 사용이 기본이라고 보는 것이 좋습니다.

---

## 4. 개발 환경에서 Broker를 사용하는 이유

개발 환경에서는 웹 애플리케이션을 간단하게 HTTP로 실행하는 경우가 많습니다.

예:

```text
http://10.10.20.30:8080
```

그러나 사내 SSO 시스템은 보안 정책상 HTTPS 기반 서비스만 허용할 수 있습니다.

이 경우 SSO Broker가 다음과 같은 HTTPS 주소를 제공할 수 있습니다.

```text
https://sso-test.company.com/my-app
```

전체 흐름은 다음과 같습니다.

```text
사용자 브라우저
        |
        | HTTPS
        v
https://sso-test.company.com/my-app
        |
        | AD SSO
        v
SSO Broker
        |
        | HTTP
        v
http://10.10.20.30:8080
        |
        v
개발 Web Application
```

이 구조에서는 사용자가 HTTP 개발 서버에 직접 접속하는 것이 아니라 Broker가 제공하는 HTTPS 주소로 접근합니다.

---

## 5. SSL/TLS 인증서의 실제 역할

SSL/TLS 인증서의 주된 역할은 두 가지입니다.

### 5.1 서버 신원 확인

브라우저는 접속한 서버가 실제 회사에서 운영하는 서버인지 인증서를 이용해 확인합니다.

예:

```text
https://sso-test.company.com
```

브라우저는 다음을 확인합니다.

```text
인증서의 도메인
        =
접속한 도메인

sso-test.company.com
```

---

### 5.2 통신 암호화

HTTPS를 사용하면 다음 구간의 통신이 암호화됩니다.

```text
Browser
   |
   | TLS 암호화
   v
SSO Broker
```

따라서 네트워크 중간에서 다음 정보가 노출되는 위험을 줄일 수 있습니다.

```text
Cookie
Token
Session ID
Authorization Header
사용자 정보
```

---

## 6. TLS Termination 구조

개발 환경에서 흔히 사용할 수 있는 구조입니다.

```text
Browser
   |
   | HTTPS
   v
Broker
   |
   | HTTP
   v
Development Server
```

Broker에서 HTTPS 연결을 종료하고 내부 개발 서버로는 HTTP 요청을 전달합니다.

이를 보통 다음과 같이 부릅니다.

```text
TLS Termination
SSL Termination
HTTPS Termination
```

구조:

```text
Internet / Client
        |
        | HTTPS
        v
+----------------------+
| SSO Broker           |
| Reverse Proxy        |
| TLS Certificate      |
+----------------------+
        |
        | HTTP
        v
+----------------------+
| Development Web App  |
+----------------------+
```

이 방식은 내부 개발망이 신뢰할 수 있는 네트워크라는 전제에서 사용할 수 있습니다.

---

## 7. TLS Re-encryption 구조

보안 요구가 높은 환경에서는 Broker와 개발 서버 사이도 HTTPS를 사용할 수 있습니다.

```text
Browser
   |
   | HTTPS
   v
Broker
   |
   | HTTPS
   v
Development Server
```

이를 다음과 같이 부를 수 있습니다.

```text
TLS Re-encryption
HTTPS Re-encryption
```

즉 Broker에서 한 번 HTTPS를 종료한 다음 다시 개발 서버와 TLS 연결을 생성합니다.

---

## 8. 두 구조 비교

### TLS Termination

```text
Browser
   |
 HTTPS
   |
Broker
   |
 HTTP
   |
Application
```

장점:

- 개발 서버 설정이 단순함
- 개발 서버에 인증서를 설치할 필요가 없을 수 있음
- 개발 환경에서 사용하기 편리함

주의점:

- Broker와 Application 사이의 통신은 암호화되지 않음

---

### TLS Re-encryption

```text
Browser
   |
 HTTPS
   |
Broker
   |
 HTTPS
   |
Application
```

장점:

- 전체 구간 암호화 가능
- 내부 네트워크에서도 민감 정보 보호

단점:

- 개발 서버에도 인증서 설정 필요
- 인증서 관리가 복잡해질 수 있음

---

## 9. 잘못 이해하기 쉬운 부분

다음과 같이 이해하면 정확하지 않습니다.

```text
HTTP 서비스이기 때문에
SSL 인증서를 이용해서
AD SSO 인증을 한다.
```

보다 정확한 표현은 다음과 같습니다.

> 개발 웹 애플리케이션은 HTTP로 동작할 수 있지만, SSO Broker가 HTTPS Endpoint를 제공하고 TLS를 종료한 뒤 내부 HTTP 개발 서버로 요청을 전달할 수 있다. SSL/TLS 인증서는 AD SSO 인증 자체가 아니라 HTTPS 통신의 암호화와 서버 신뢰를 제공한다.

---

## 10. 예상되는 SSO Broker 구조

사내 Broker가 다음 정보를 요구한다고 가정합니다.

```text
Service Name
Service URL
Callback URL
Redirect URL
SSL Certificate
```

예:

```text
Service Name:
DEV-MY-SERVICE

Service URL:
http://10.20.30.40:8080

Broker URL:
https://sso-dev.company.com/my-service

Redirect URI:
https://sso-dev.company.com/my-service/callback
```

예상 구조:

```text
                    +-----------------------+
                    | Active Directory      |
                    +-----------+-----------+
                                |
                                | 인증
                                |
+---------+     HTTPS     +-----v-----------+
| Browser | ------------> | SSO Broker      |
+---------+                | Reverse Proxy   |
                           +-------+---------+
                                   |
                                   | HTTP
                                   |
                           +-------v---------+
                           | Dev Web App     |
                           | :8080           |
                           +-----------------+
```

---

## 11. OIDC 방식일 경우의 흐름 예시

SSO Broker가 OIDC를 사용하는 경우 대략 다음과 같이 동작할 수 있습니다.

```text
1. 사용자가 서비스 접속

https://sso-dev.company.com/my-app
```

```text
2. Broker에서 인증 여부 확인
```

인증되지 않았다면 AD 인증으로 이동합니다.

```text
Browser
   |
   v
SSO Broker
   |
   v
AD Login / Kerberos
```

```text
3. AD 인증 성공
```

Broker 또는 Identity Provider가 사용자 인증 정보를 생성합니다.

예:

```text
ID Token
Access Token
User Claims
```

예시 Claim:

```json
{
  "sub": "user123",
  "name": "Hong Gil Dong",
  "email": "user@company.com",
  "department": "IT"
}
```

```text
4. Broker가 개발 웹으로 요청 전달
```

```text
Broker
   |
   | HTTP
   v
http://dev-server:8080
```

---

## 12. SAML 방식일 경우

SAML 기반 환경이라면 다음 용어가 나타날 수 있습니다.

```text
IdP
SP
SAML Response
Assertion
ACS URL
Metadata XML
Entity ID
```

구조:

```text
사용자
   |
   v
SP / Broker
   |
   v
AD / IdP
   |
   | SAML Assertion
   v
Broker
   |
   v
Web Application
```

개발자가 특히 확인해야 할 값:

```text
Entity ID
ACS URL
Redirect URL
Logout URL
Metadata URL
```

---

## 13. Kerberos 기반 AD SSO

사내 Windows 환경에서는 Kerberos 기반 인증이 사용될 수도 있습니다.

예:

```text
Windows 로그인
      |
      v
Kerberos Ticket
      |
      v
Browser
      |
      v
SSO Broker
```

사용자가 이미 Windows 도메인에 로그인되어 있다면 별도의 ID/PW 입력 없이 인증될 수 있습니다.

관련 키워드:

```text
Kerberos
SPNEGO
NTLM
Integrated Windows Authentication
IWA
Domain
KDC
SPN
```

---

## 14. 인증서 파일 확장자 이해

회사에서 다음과 같은 인증서를 제공할 수 있습니다.

```text
.cer
.crt
.pem
.pfx
.p12
```

확장자만 보고 정확한 역할을 단정할 수는 없지만 일반적으로 다음처럼 볼 수 있습니다.

### `.crt`, `.cer`

주로 공개 인증서입니다.

용도 예:

```text
회사 CA 인증서 신뢰
Broker 서버 인증서 신뢰
```

Private Key는 포함되지 않는 경우가 많습니다.

---

### `.pem`

다음 내용을 포함할 수 있습니다.

```text
Certificate
Private Key
CA Certificate
Certificate Chain
```

따라서 파일 내용을 확인해야 합니다.

예:

```text
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
```

---

### `.pfx`, `.p12`

PKCS#12 형식입니다.

대체로 다음을 함께 포함할 수 있습니다.

```text
Server Certificate
Private Key
Certificate Chain
```

일반적으로 비밀번호가 설정됩니다.

개발 서버에서 직접 HTTPS를 실행해야 한다면 이러한 파일이 제공될 가능성이 있습니다.

---

## 15. 개발 서버에 인증서를 설치하는 경우

Broker가 TLS Termination을 한다면 개발 애플리케이션은 HTTP로 실행될 수 있습니다.

```text
Broker HTTPS
   |
   v
HTTP App
```

따라서 애플리케이션 서버에 SSL 인증서를 설치하지 않을 수도 있습니다.

반대로 다음 구조라면 개발 서버에도 인증서가 필요할 수 있습니다.

```text
Broker
   |
 HTTPS
   |
App Server
```

예:

```text
https://dev-server.company.local:8443
```

---

## 16. Web 개발 시 확인해야 할 핵심 설정

SSO 연동을 시작하기 전에 다음 항목을 확인하는 것이 좋습니다.

### 서비스 URL

```text
http://dev-server:8080
```

Broker가 실제 요청을 전달하는 대상입니다.

---

### Broker URL

```text
https://sso-dev.company.com/my-app
```

사용자가 실제로 접속하는 주소일 수 있습니다.

---

### Redirect URI

OIDC 인증 후 돌아오는 주소입니다.

예:

```text
https://sso-dev.company.com/my-app/callback
```

OIDC 시스템에서는 Redirect URI가 사전에 등록된 값과 정확히 일치해야 하는 경우가 많습니다.

---

### SAML ACS URL

SAML 인증 결과를 전달받는 주소입니다.

예:

```text
https://sso-dev.company.com/my-app/saml/acs
```

---

### Logout URL

로그아웃 이후 이동하는 URL입니다.

예:

```text
https://sso-dev.company.com/my-app/logout
```

---

## 17. Reverse Proxy를 사용할 때 주의할 Header

Broker 또는 Reverse Proxy 뒤에서 동작하는 애플리케이션은 원래 사용자가 HTTPS로 접속했다는 사실을 알아야 할 수 있습니다.

대표 Header:

```text
X-Forwarded-Proto
X-Forwarded-Host
X-Forwarded-For
Forwarded
```

예:

```http
X-Forwarded-Proto: https
X-Forwarded-Host: sso-dev.company.com
X-Forwarded-For: 10.10.10.100
```

특히 다음 문제가 발생할 때 중요합니다.

```text
Redirect URL이 http로 생성됨
Callback URL이 잘못 생성됨
Secure Cookie가 동작하지 않음
OAuth Redirect URI mismatch 발생
```

---

## 18. 개발 Web Application에서의 HTTPS 인식

개발 서버는 실제로 HTTP 요청을 받고 있을 수 있습니다.

```text
Broker
   |
 HTTP
   |
App
```

하지만 사용자 기준에서는 HTTPS입니다.

```text
Browser
   |
 HTTPS
   |
Broker
```

따라서 Web Framework에서는 Proxy Header를 신뢰하도록 설정해야 할 수 있습니다.

예를 들어 애플리케이션 내부에서 다음 URL을 만들어야 합니다.

```text
https://sso-dev.company.com/callback
```

그런데 Proxy 설정이 잘못되어 있으면 다음처럼 생성될 수 있습니다.

```text
http://sso-dev.company.com/callback
```

이 경우 OIDC 인증에서 Redirect URI mismatch가 발생할 수 있습니다.

---

## 19. FastAPI 환경에서의 예시

개발 서버:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Broker 내부 Target:

```text
http://10.20.30.40:8000
```

사용자 접속:

```text
https://sso-dev.company.com/my-api
```

Proxy 환경에서는 Uvicorn의 Proxy Header 설정이 필요할 수 있습니다.

예:

```bash
uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --proxy-headers
```

신뢰할 수 있는 Proxy IP를 제한하는 것도 중요합니다.

환경에 따라:

```bash
--forwarded-allow-ips
```

설정을 검토합니다.

---

## 20. Spring Boot 환경에서 확인할 내용

Spring Boot를 Reverse Proxy 뒤에서 사용할 경우 Forwarded Header 처리가 필요할 수 있습니다.

예:

```properties
server.forward-headers-strategy=framework
```

환경과 Spring Boot 버전에 따라 설정 방식이 다를 수 있으므로 사내 표준을 우선 확인해야 합니다.

---

## 21. Node.js / Express 환경

Express에서 Proxy를 사용하는 경우:

```javascript
app.set('trust proxy', true);
```

이 설정을 사용할 수 있습니다.

다만 무조건 `true`로 설정하기보다는 실제 Proxy 구조에 맞게 제한하는 것이 안전합니다.

예:

```javascript
app.set('trust proxy', 'loopback');
```

또는 사내 Proxy IP 대역을 지정합니다.

---

## 22. Cookie 설정

SSO 환경에서는 Session Cookie 또는 인증 Cookie의 설정도 중요합니다.

운영 HTTPS 환경에서는 일반적으로 다음을 고려합니다.

```text
Secure
HttpOnly
SameSite
```

예:

```http
Set-Cookie:
session=abc123;
Secure;
HttpOnly;
SameSite=Lax
```

### Secure

HTTPS 연결에서만 Cookie가 전달되도록 합니다.

### HttpOnly

JavaScript에서 Cookie 접근을 제한하여 XSS 피해를 줄입니다.

### SameSite

Cross-Site 요청에서 Cookie 전달 정책을 제어합니다.

OIDC/SAML 환경에서는 인증 흐름에 따라 `SameSite` 설정이 영향을 줄 수 있으므로 주의해야 합니다.

---

## 23. 개발 중 자주 발생하는 문제

### 23.1 Redirect URI mismatch

에러 예:

```text
Invalid redirect_uri
Redirect URI mismatch
```

확인:

```text
Broker 등록 URI
Application Callback URI
Protocol(http/https)
Host
Port
Path
```

모두 정확히 일치하는지 확인합니다.

---

### 23.2 HTTP ↔ HTTPS Redirect Loop

증상:

```text
Too many redirects
ERR_TOO_MANY_REDIRECTS
```

원인 중 하나:

```text
Browser -> HTTPS Broker
Broker -> HTTP Application

Application:
"HTTP 요청이네? HTTPS로 보내야겠다."

다시 Broker로 redirect
```

결과:

```text
HTTPS
 -> HTTP
 -> HTTPS
 -> HTTP
 -> ...
```

이 경우 `X-Forwarded-Proto` 처리가 중요합니다.

---

### 23.3 인증 후 다시 로그인 화면으로 이동

가능한 원인:

```text
Session Cookie 미저장
Secure Cookie 문제
SameSite 문제
Domain 문제
Broker Session 문제
Callback URL 문제
```

---

### 23.4 인증서 오류

브라우저 오류:

```text
NET::ERR_CERT_AUTHORITY_INVALID
NET::ERR_CERT_COMMON_NAME_INVALID
```

가능한 원인:

```text
회사 CA가 PC에 등록되지 않음
인증서 도메인 불일치
인증서 만료
Certificate Chain 누락
```

---

## 24. 회사에서 인증서를 제공할 때 확인할 질문

SSO 담당자에게 다음 내용을 확인하면 구조를 빠르게 이해할 수 있습니다.

```text
1. 제공된 인증서는 어떤 용도인가?

2. Broker HTTPS 접속을 신뢰하기 위한 CA 인증서인가?

3. 개발 서버 자체 HTTPS 구성을 위한 서버 인증서인가?

4. Private Key가 포함되어 있는가?

5. 인증서를 개발 서버에 설치해야 하는가?

6. 사용자 PC에 CA 인증서를 설치해야 하는가?

7. Broker -> Application 구간은 HTTP인가 HTTPS인가?

8. Application Service URL은 어떤 값을 등록해야 하는가?

9. Redirect URI 또는 Callback URI는 어떤 값을 등록해야 하는가?

10. Broker가 전달하는 인증 사용자 정보는 어떤 Header/Token 형태인가?
```

---

## 25. 가장 중요한 구조 확인 질문

SSO 담당자에게 다음 질문 하나만 해도 구조를 상당 부분 파악할 수 있습니다.

> Broker 서버가 HTTPS 요청을 받은 뒤 개발 애플리케이션으로 HTTP Reverse Proxy를 수행하는 TLS Termination 구조인가요? 아니면 Broker와 개발 애플리케이션 사이도 HTTPS를 사용하는 Re-encryption 구조인가요?

---

## 26. 보안상 주의사항

### 개발 서버를 외부망에 직접 노출하지 않기

다음 형태는 피하는 것이 좋습니다.

```text
Internet
   |
   v
http://dev-server:8080
```

가능하면:

```text
User
 |
 HTTPS
 |
Broker
 |
Internal Network
 |
Dev Server
```

구조를 사용합니다.

---

### Token 로그 출력 주의

개발 중 다음 정보를 로그에 그대로 출력하지 않는 것이 좋습니다.

```text
Access Token
ID Token
Refresh Token
Session Cookie
Authorization Header
```

---

### Secret은 소스 코드에 직접 저장하지 않기

예:

```text
Client Secret
Private Key
Password
API Key
```

잘못된 예:

```python
CLIENT_SECRET = "abc123-secret"
```

권장:

```text
Environment Variable
Kubernetes Secret
Vault
사내 Secret Manager
```

예:

```python
import os

CLIENT_SECRET = os.getenv("CLIENT_SECRET")
```

---

## 27. 전체 개념 정리

사내 개발 환경에서 다음과 같은 상황이 있다고 가정합니다.

```text
개발 Web
http://dev-server:8080
```

그리고 사내 SSO Broker가 존재합니다.

```text
https://sso-dev.company.com
```

가장 가능성이 높은 구조는 다음과 같습니다.

```text
+-------------+
|   Browser   |
+------+------+
       |
       | HTTPS
       | TLS Certificate
       |
+------v------------------+
| SSO Broker              |
| Reverse Proxy           |
| AD Authentication       |
+------+------------------+
       |
       | HTTP
       |
+------v------------------+
| Development Web App     |
| http://dev-server:8080  |
+-------------------------+
```

이때:

```text
AD
 = 사용자 인증

SSO Broker
 = 인증 중계

SSL/TLS Certificate
 = HTTPS 통신 보호

HTTP Development Server
 = 실제 개발 중인 Application
```

입니다.

---

## 28. 한 문장으로 정리

> 개발 웹이 HTTP로 실행되더라도 SSO Broker가 앞단에서 HTTPS와 AD SSO 인증을 제공하고, TLS를 종료한 뒤 내부 HTTP 개발 서버로 요청을 전달하는 방식으로 개발 단계의 SSO 테스트 환경을 구성할 수 있다. 이때 SSL/TLS 인증서는 AD 인증을 수행하는 것이 아니라 사용자와 Broker 사이의 통신을 암호화하고 Broker 서버의 신원을 검증하는 역할을 한다.

---

## 29. 개발자가 기억해야 할 핵심 5가지

1. **AD 인증과 HTTPS는 서로 다른 기능이다.**
2. **SSL 인증서가 SSO 인증 자체를 수행하는 것은 아니다.**
3. **Broker가 HTTPS를 종료하고 HTTP 개발 서버로 전달할 수 있다.**
4. **Reverse Proxy 환경에서는 `X-Forwarded-*` Header 처리가 중요하다.**
5. **Redirect URI, Cookie, Proxy 설정이 SSO 개발에서 가장 자주 문제를 일으킨다.**

---

## 30. 실제 연동 전에 확보하면 좋은 정보

사내 SSO 담당 부서로부터 아래 정보를 받으면 개발을 시작하기 쉽습니다.

```text
SSO Protocol
- OIDC?
- OAuth2?
- SAML?
- Kerberos?
- 사내 자체 방식?

Broker URL

Service URL 등록 방법

Redirect URI / Callback URL

Logout URL

Client ID

Client Secret 필요 여부

Certificate 종류

CA Certificate 필요 여부

Broker -> Application 통신 방식
- HTTP
- HTTPS

사용자 정보 전달 방식
- HTTP Header
- JWT
- ID Token
- SAML Assertion

개발/운영 환경 분리 여부
```

이 정보를 확보하면 전체 SSO 구조를 정확하게 설계할 수 있습니다.
