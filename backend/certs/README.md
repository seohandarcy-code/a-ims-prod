# 내부 CA 인증서 폴더 (로컬 전용)

사내 SSO 브로커(ADFS 등)가 내부 CA 인증서를 쓸 때, 여기에 그 CA의 PEM
파일을 넣고 `backend/.env`의 `SSO_CA_BUNDLE_PATH`에 파일명을 적는다.

이 폴더 안의 실제 인증서 파일은 git에 커밋되지 않는다(`.gitignore` 참고) —
이 `README.md`만 커밋 대상이다.

PDEP 등 실제 배포 환경에서는 이 폴더 대신 K8s Secret을 Volume으로 마운트해
인증서를 주입한다. 자세한 내용은 `docs/ENV_AND_SECRETS.md`의
`SSO_CA_BUNDLE_PATH` 설명 참고.
