#!/usr/bin/env bash
# 간단한 ngrok 실행 스크립트 (Raspberry Pi용)
# 사용법: ./ngrok.sh [포트]
# 예시:  ./ngrok.sh           # 기본 5000 포트로 터널 오픈
#        ./ngrok.sh 5000      # 5000 포트로 터널 오픈

set -Eeuo pipefail

# 스크립트 경로 기준 설정 파일
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN_FILE="$SCRIPT_DIR/domain.txt"

# 포트 인자 처리 (기본값 5000)
PORT="${1:-5000}"

# ngrok 설치 확인
if ! command -v ngrok >/dev/null 2>&1; then
	echo "[ERROR] ngrok 명령을 찾을 수 없습니다. 먼저 ngrok을 설치하세요: https://ngrok.com/download"
	exit 1
fi

# 선택: 환경변수 NGROK_AUTHTOKEN 이 있으면 자동 등록
if [ "${NGROK_AUTHTOKEN:-}" != "" ]; then
	echo "[INFO] NGROK_AUTHTOKEN 감지됨. 설정 적용 시도..."
	ngrok config add-authtoken "$NGROK_AUTHTOKEN" || true
fi

# DOMAIN 결정 순서
# 1) 환경변수 NGROK_DOMAIN
# 2) domain.txt 첫 번째 유효 라인(주석/빈줄 제외)
DOMAIN="${NGROK_DOMAIN:-}"
if [ -z "$DOMAIN" ]; then
	if [ -f "$DOMAIN_FILE" ]; then
		# 첫 번째 유효 라인 읽기
		DOMAIN="$(grep -E -v '^\s*(#|$)' "$DOMAIN_FILE" | head -n1 || true)"
	fi
fi

# 스킴이 포함된 경우 제거 (예: https://example.ngrok-free.app)
if [[ "${DOMAIN}" =~ ^https?:// ]]; then
	DOMAIN="${DOMAIN#http://}"
	DOMAIN="${DOMAIN#https://}"
fi

if [ -z "$DOMAIN" ]; then
	echo "[ERROR] 도메인을 찾을 수 없습니다. 다음 중 하나를 설정하세요:"
	echo "        1) 환경변수 NGROK_DOMAIN"
	echo "        2) 파일 $DOMAIN_FILE 에 도메인(host) 한 줄 입력 (예: joey-joint-redbird.ngrok-free.app)"
	exit 1
fi

echo "[INFO] ngrok 터널 시작: https://$DOMAIN -> http://localhost:$PORT"
echo "[INFO] 중지는 Ctrl+C 를 누르세요."

# 참고: --region 설정이 필요한 경우 --region=ap 와 같이 추가하세요.
exec ngrok http --url="$DOMAIN" "$PORT"

ngrok http --url=joey-joint-redbird.ngrok-free.app 5000