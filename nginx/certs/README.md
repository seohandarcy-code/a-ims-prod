# 로컬 HTTPS용 자체 서명 인증서 폴더

`scripts\setup-local-https.ps1`이 생성하는 `dev-selfsigned.crt`/
`dev-selfsigned.key`가 여기에 들어간다. 개인키가 포함된 파일이라 git에
커밋되지 않는다(`.gitignore` 참고) — 이 `README.md`만 커밋 대상이다.

사용법은 `scripts\setup-local-https.ps1` 상단 주석과 `README.md`의
"다른 서버로 옮겨서 실제 SSO 브로커에 연동하기" H번 절 참고.

이 폴더에 인증서가 없으면 `scripts\start-dev.ps1`은 지금까지처럼 HTTP만
리슨한다 — 이 기능 자체를 몰라도 아무 영향 없다.
