"""Modular webhook server for TradingView signals and Discord bot.

Modular Flask server with separate API blueprints for:
- TradingView webhooks
- Discord bot integration
- Trading operations

Port: 5000 (HTTPS if certs provided or adhoc enabled; otherwise HTTP)

Environment variables (optional):
- SSL_CERT_FILE: path to TLS certificate (PEM)
- SSL_KEY_FILE: path to TLS private key (PEM)
- USE_ADHOC_SSL: "1" to try Flask's adhoc cert (requires 'cryptography')
"""

from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, send_from_directory

# API Blueprints import
from .api.discord_api import discord_bp
from .api.tradingview_api import tradingview_bp
from .api.trading_api import trading_bp

# 모듈 import
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from module.upbit_api import UpbitAPI
from module.trading_executor import TradingExecutor
from module.logging_utils import setup_server_logging

log = logging.getLogger(__name__)

# web2 폴더의 static 폴더 경로 설정
web2_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web2')
static_path = os.path.join(web2_path, 'static')

app = Flask(__name__, static_folder=static_path, static_url_path='/static')

# Blueprint 등록
app.register_blueprint(discord_bp)
app.register_blueprint(tradingview_bp)
app.register_blueprint(trading_bp)

# 전역 인스턴스 (레거시 호환성을 위해 유지)
upbit_api = UpbitAPI()
trading_executor = TradingExecutor(upbit_api)


# 기본 라우트들
@app.route("/", methods=["GET"])
def root():
    """메인 대시보드 페이지 제공"""
    return send_from_directory(web2_path, 'index.html')


@app.route("/api-info", methods=["GET"])
def api_info():
    """API 정보 제공 (기존 루트 엔드포인트 내용)"""
    return jsonify({
        "service": "Auto Trading Server",
        "version": "2.0.0",
        "status": "running",
        "apis": {
            "discord": "/api/discord",
            "tradingview": "/api/tradingview", 
            "trading": "/api/trading"
        },
        "endpoints": {
            "health": "/health",
            "legacy_ta_signal": "/ta-signal",
            "legacy_ta_signal_test": "/ta-signal-test"
        }
    }), 200


@app.route("/health", methods=["GET"])
def health():
    """전체 시스템 상태 확인"""
    return jsonify({
        "status": "up",
        "service": "auto-trading-server",
        "version": "2.0.0",
        "apis": {
            "discord": "active",
            "tradingview": "active", 
            "trading": "active"
        }
    }), 200


# 레거시 호환성을 위한 라우트들 (기존 TradingView 웹훅이 계속 작동하도록)
@app.route("/ta-signal-test", methods=["POST"])
def legacy_ta_signal_test():
    """레거시 호환성: /ta-signal-test -> /api/tradingview/signal-test로 리다이렉트"""
    from .api.tradingview_api import ta_signal_test
    return ta_signal_test()


@app.route("/ta-signal", methods=["POST"])  
def legacy_ta_signal():
    """레거시 호환성: /ta-signal -> /api/tradingview/signal로 리다이렉트"""
    from .api.tradingview_api import ta_signal
    return ta_signal()


# 레거시 엔드포인트들도 새로운 API로 리다이렉트
@app.route("/test-balance", methods=["GET"])
def legacy_test_balance():
    """레거시 호환성: /test-balance -> /api/trading/balance로 리다이렉트"""
    from .api.trading_api import get_balance
    return get_balance()


@app.route("/markets", methods=["GET"])
def legacy_markets():
    """레거시 호환성: /markets -> /api/trading/markets로 리다이렉트"""
    from .api.trading_api import get_markets
    return get_markets()


@app.route("/trading-config", methods=["GET"])
def legacy_trading_config():
    """레거시 호환성: /trading-config -> /api/trading/config로 리다이렉트"""
    from .api.trading_api import get_trading_config
    return get_trading_config()


def _get_ssl_context():
	"""Return an SSL context tuple or 'adhoc' if configured; otherwise None.

	Priority:
	1) If SSL_CERT_FILE and SSL_KEY_FILE are set and exist, use those.
	2) If USE_ADHOC_SSL=1, try 'adhoc' (requires 'cryptography').
	3) Else return None (HTTP).
	"""
	cert = os.getenv("SSL_CERT_FILE")
	key = os.getenv("SSL_KEY_FILE")
	if cert and key and os.path.exists(cert) and os.path.exists(key):
		log.info("Using provided SSL certificate and key.")
		return cert, key

	if os.getenv("USE_ADHOC_SSL") == "1":
		try:
			# Werkzeug will lazily create an adhoc cert if 'cryptography' is available
			log.info("Using adhoc SSL certificate.")
			return "adhoc"
		except Exception as e:  # pragma: no cover - defensive
			log.warning("Failed to enable adhoc SSL (%s); falling back to HTTP.", e)

	return None


def run_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = False) -> None:
	"""Run the webhook server.

	Args:
		host: Bind address. Defaults to 0.0.0.0
		port: Port to listen on. Defaults to 5000
		debug: Flask debug mode.
	"""
	# 로깅 설정
	setup_server_logging()

	# 업비트 API 초기화 (이미 __init__에서 처리됨)
	log.info("업비트 마켓 정보를 로드 중입니다...")
	if upbit_api.market_info_cache:
		log.info("마켓 정보 로드 완료. 지원 가능한 티커 수: %d", len(upbit_api.market_info_cache))
	else:
		log.warning("마켓 정보 로드 실패. 티커 매칭이 제한될 수 있습니다.")

	ssl_context = _get_ssl_context()
	scheme = "HTTPS" if ssl_context else "HTTP"
	log.info("Starting %s server on %s:%s", scheme, host, port)
	print(f"Starting {scheme} server on {host}:{port}")

	# Note: For production, consider a WSGI server (gunicorn, waitress) behind a reverse proxy.
	app.run(host=host, port=port, debug=debug, ssl_context=ssl_context, use_reloader=False)


__all__ = ["run_server", "app"]

