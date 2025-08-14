"""Simple webhook server for TradingView signals.

Exposes POST /ta-signal and prints incoming payloads.
Intended to be started from main.py via server.run_server().

Port: 443 (HTTPS if certs provided or adhoc enabled; otherwise HTTP)

Environment variables (optional):
- SSL_CERT_FILE: path to TLS certificate (PEM)
- SSL_KEY_FILE: path to TLS private key (PEM)
- USE_ADHOC_SSL: "1" to try Flask's adhoc cert (requires 'cryptography')
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from flask import Flask, request, jsonify

# 모듈 import
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from module.upbit_api import UpbitAPI
from module.trading_executor import TradingExecutor
from module.logging_utils import SignalLogger, setup_server_logging

log = logging.getLogger(__name__)

app = Flask(__name__)

# 전역 인스턴스
upbit_api = UpbitAPI()
trading_executor = TradingExecutor(upbit_api)
signal_logger = SignalLogger()


"""
메세지 형태.
{
	"strategy": {
		"name": "SMI/RSI",
		"settings": {
			"source": "[B]",
			"parameters": "20, 20, 1.5, 14, 5, 2"
		}
	},
	"instrument": {
		"ticker": "{{ticker}}"
	},
	"order": {
		"action": "{{strategy.order.action}}",
		"quantity": "{{strategy.order.contracts}}"
	},
	"position": {
		"new_size": "{{strategy.position_size}}"
	}
}

"""
@app.route("/ta-signal-test", methods=["POST"])
def ta_signal_test():
	"""Receive TradingView webhook payload and log it to file.

	Accepts JSON or raw text. Returns a simple JSON ack.
	"""
	try:
		payload: Dict[str, Any] | None = None
		text_body: str | None = None

		if request.is_json:
			payload = request.get_json(silent=True)
		else:
			text_body = request.get_data(as_text=True)

		# Log to console
		if payload is not None:
			log.info("[TA-TEST] JSON payload: %s", json.dumps(payload, ensure_ascii=False))
			print("[TA-TEST] JSON payload:", json.dumps(payload, ensure_ascii=False))
			# Log to file
			signal_logger.log_ta_signal_to_file(payload, "ta-signal-test")
		else:
			log.info("[TA-TEST] Text payload: %s", text_body)
			print("[TA-TEST] Text payload:", text_body)
			# Log to file
			signal_logger.log_ta_signal_to_file(text_body or "", "ta-signal-test")

		return jsonify({"status": "ok"}), 200
	except Exception as e:
		log.exception("Error handling /ta-signal-test: %s", e)
		return jsonify({"status": "error", "message": str(e)}), 500


"""
curl -X POST http://localhost:5000/ta-signal \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": {
      "name": "Test Strategy"
    },
    "instrument": {
      "ticker": "BTC"
    },
    "order": {
      "action": "buy",
      "quantity": "1"
    },
    "position": {
      "new_size": "1"
    }
  }'
"""
@app.route("/ta-signal", methods=["POST"])
def ta_signal():
	"""TradingView에서 웹훅을 받아 업비트 매매 신호 실행"""
	try:
		payload: Dict[str, Any] | None = None
		text_body: str | None = None

		if request.is_json:
			payload = request.get_json(silent=True)
		else:
			text_body = request.get_data(as_text=True)

		# 로그 출력
		if payload is not None:
			log.info("[TA] JSON payload: %s", json.dumps(payload, ensure_ascii=False))
			print("[TA] JSON payload:", json.dumps(payload, ensure_ascii=False))
			
			# 파일에 로그 저장
			signal_logger.log_ta_signal_to_file(payload, "ta-signal")
			
			# JSON 데이터에서 매매 신호 추출 및 실행
			try:
				ticker = payload.get("instrument", {}).get("ticker", "")
				action = payload.get("order", {}).get("action", "").lower()
				
				if not ticker:
					log.warning("티커 정보가 없습니다.")
					return jsonify({"status": "error", "message": "Missing ticker"}), 400
				
				if not action:
					log.warning("액션 정보가 없습니다.")
					return jsonify({"status": "error", "message": "Missing action"}), 400
				
				log.info("매매 신호 처리: 티커=%s, 액션=%s", ticker, action)
				
				if action == "buy":
					success = trading_executor.execute_buy_signal(ticker)
					if success:
						return jsonify({"status": "ok", "message": f"Buy order executed for {ticker}"}), 200
					else:
						return jsonify({"status": "error", "message": f"Buy order failed for {ticker}"}), 500
				
				elif action == "sell":
					success = trading_executor.execute_sell_signal(ticker)
					if success:
						return jsonify({"status": "ok", "message": f"Sell order executed for {ticker}"}), 200
					else:
						return jsonify({"status": "error", "message": f"Sell order failed for {ticker}"}), 500
				
				else:
					log.warning("알 수 없는 액션: %s", action)
					return jsonify({"status": "ok", "message": f"Unknown action: {action}"}), 200
					
			except Exception as trading_error:
				log.error("매매 신호 처리 중 오류: %s", trading_error)
				return jsonify({"status": "error", "message": f"Trading error: {str(trading_error)}"}), 500
			
		else:
			log.info("[TA] Text payload: %s", text_body)
			print("[TA] Text payload:", text_body)
			# 파일에 로그 저장
			signal_logger.log_ta_signal_to_file(text_body or "", "ta-signal")

		return jsonify({"status": "ok"}), 200
	except Exception as e:
		log.exception("Error handling /ta-signal: %s", e)
		return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/health", methods=["GET"])  # simple liveness probe
def health():
	return jsonify({"status": "up"}), 200

@app.route("/test-balance", methods=["GET"])
def test_balance():
	"""업비트 잔고 조회 테스트"""
	try:
		balances = upbit_api.get_balances()
		total_balance = upbit_api.calculate_total_balance()
		
		return jsonify({
			"status": "ok", 
			"balances": balances,
			"total_balance_krw": total_balance
		}), 200
	except Exception as e:
		log.error("잔고 조회 테스트 중 오류: %s", e)
		return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/markets", methods=["GET"])
def get_markets():
	"""지원 가능한 마켓 및 티커 목록 조회"""
	try:
		available_tickers = upbit_api.get_available_tickers()
		market_details = {}
		
		# 상위 20개 주요 코인만 상세 정보 포함
		major_tickers = ['BTC', 'ETH', 'XRP', 'ADA', 'DOT', 'LINK', 'LTC', 'BCH', 'EOS', 'TRX', 
						'ETC', 'ATOM', 'BAT', 'ENJ', 'KNC', 'MANA', 'SAND', 'AXS', 'CHZ', 'FLOW']
		
		for ticker in major_tickers:
			if ticker in upbit_api.market_info_cache:
				market_details[ticker] = upbit_api.market_info_cache[ticker]
		
		return jsonify({
			"status": "ok",
			"total_markets": len(available_tickers),
			"all_tickers": sorted(available_tickers),
			"major_markets": market_details
		}), 200
	except Exception as e:
		log.error("마켓 조회 중 오류: %s", e)
		return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/trading-config", methods=["GET"])
def get_trading_config():
	"""현재 매매 전략 설정값 조회"""
	try:
		config = trading_executor.get_trading_config()
		return jsonify({
			"status": "ok",
			"config": config,
			"description": {
				"max_position_ratio": "각 종목 최대 비중 (전체 자산 대비)",
				"min_order_amount": "최소 주문 금액 (원)",
				"min_sell_value": "최소 매도 가치 (원)"
			}
		}), 200
	except Exception as e:
		log.error("설정 조회 중 오류: %s", e)
		return jsonify({"status": "error", "message": str(e)}), 500


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

