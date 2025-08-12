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
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import jwt
import uuid
import requests
import hashlib
from urllib.parse import urlencode, unquote

from flask import Flask, request, jsonify


log = logging.getLogger(__name__)

app = Flask(__name__)

# 업비트 API 키 (전역 변수)
ACCESS_KEY = ''
SECRET_KEY = ''

def read_upbit_keys():
	"""업비트 API 키를 파일에서 읽어옴"""
	global ACCESS_KEY, SECRET_KEY
	try:
		with open('./private/keys.json', 'r') as f:
			keys = json.load(f)
			ACCESS_KEY = keys['COIN'][0]['APP_KEY']
			SECRET_KEY = keys['COIN'][0]['APP_SECRET']
			log.info("업비트 API 키를 성공적으로 로드했습니다.")
	except Exception as e:
		log.error("업비트 API 키 로드 실패: %s", e)

def make_upbit_token(query_params=None):
	"""업비트 JWT 토큰 생성"""
	payload = {
		'access_key': ACCESS_KEY,
		'nonce': str(uuid.uuid4()),
	}
	
	if query_params:
		query_string = unquote(urlencode(query_params, doseq=True)).encode("utf-8")
		m = hashlib.sha512()
		m.update(query_string)
		query_hash = m.hexdigest()
		payload['query_hash'] = query_hash
		payload['query_hash_alg'] = 'SHA512'
	
	jwt_token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
	return f'Bearer {jwt_token}'

def get_upbit_balances():
	"""업비트 잔고 조회"""
	try:
		url = 'https://api.upbit.com/v1/accounts'
		headers = {'Authorization': make_upbit_token()}
		
		response = requests.get(url, headers=headers)
		if response.status_code == 200:
			return response.json()
		else:
			log.error("잔고 조회 실패: %s", response.text)
			return None
	except Exception as e:
		log.error("잔고 조회 중 오류: %s", e)
		return None

def get_current_price(market):
	"""특정 마켓의 현재가 조회"""
	try:
		url = "https://api.upbit.com/v1/ticker"
		params = {"markets": market}
		
		response = requests.get(url, params=params)
		if response.status_code == 200:
			data = response.json()
			return data[0]['trade_price'] if data else None
		else:
			log.error("현재가 조회 실패: %s", response.text)
			return None
	except Exception as e:
		log.error("현재가 조회 중 오류: %s", e)
		return None

def calculate_total_balance():
	"""전체 보유 자산 계산 (KRW 기준)"""
	try:
		balances = get_upbit_balances()
		if not balances:
			return 0
		
		total_krw = 0
		
		for balance in balances:
			currency = balance['currency']
			balance_amount = float(balance['balance'])
			
			if currency == 'KRW':
				total_krw += balance_amount
			else:
				# 다른 코인의 경우 KRW 가격으로 환산
				market = f'KRW-{currency}'
				current_price = get_current_price(market)
				if current_price:
					total_krw += balance_amount * current_price
		
		return total_krw
	except Exception as e:
		log.error("전체 잔고 계산 중 오류: %s", e)
		return 0

def place_upbit_order(market, side, volume=None, price=None, ord_type='market'):
	"""업비트 주문 실행"""
	try:
		url = 'https://api.upbit.com/v1/orders'
		
		params = {
			'market': market,
			'side': side,  # 'bid' (매수) 또는 'ask' (매도)
			'ord_type': ord_type,  # 'market' (시장가) 또는 'limit' (지정가)
		}
		
		if side == 'bid' and ord_type == 'market':
			# 매수: 시장가 매수 시 price (총 금액) 사용
			if price:
				params['price'] = str(int(price))
		elif side == 'ask':
			# 매도: volume (수량) 사용
			if volume:
				params['volume'] = str(volume)
		
		headers = {'Authorization': make_upbit_token(params)}
		
		response = requests.post(url, json=params, headers=headers)
		if response.status_code == 201:
			log.info("주문 성공: %s", response.json())
			return response.json()
		else:
			log.error("주문 실패: %s", response.text)
			return None
	except Exception as e:
		log.error("주문 실행 중 오류: %s", e)
		return None

def execute_buy_signal(ticker):
	"""매수 신호 실행 - 전체 자산의 20%로 매수"""
	try:
		# KRW- 형태로 마켓 코드 생성
		market = f'KRW-{ticker}' if not ticker.startswith('KRW-') else ticker
		
		# 전체 자산의 20% 계산
		total_balance = calculate_total_balance()
		buy_amount = total_balance * 0.2
		
		# 최소 주문 금액 확인 (업비트 최소 주문 금액: 5000원)
		if buy_amount < 5000:
			log.warning("매수 금액이 최소 주문 금액보다 작습니다: %s원", buy_amount)
			return False
		
		# 시장가 매수 주문
		result = place_upbit_order(market, 'bid', price=buy_amount, ord_type='market')
		
		if result:
			log.info("매수 주문 성공 - 마켓: %s, 금액: %s원", market, buy_amount)
			return True
		else:
			log.error("매수 주문 실패 - 마켓: %s", market)
			return False
	except Exception as e:
		log.error("매수 신호 실행 중 오류: %s", e)
		return False

def execute_sell_signal(ticker):
	"""매도 신호 실행 - 해당 코인 전량 매도"""
	try:
		# 코인 심볼 추출 (KRW- 제거)
		coin_symbol = ticker.replace('KRW-', '') if ticker.startswith('KRW-') else ticker
		
		# 잔고에서 해당 코인 수량 확인
		balances = get_upbit_balances()
		if not balances:
			log.error("잔고 조회 실패")
			return False
		
		coin_balance = None
		for balance in balances:
			if balance['currency'] == coin_symbol:
				coin_balance = float(balance['balance'])
				break
		
		if not coin_balance or coin_balance <= 0:
			log.warning("매도할 %s 코인이 없습니다.", coin_symbol)
			return False
		
		# 마켓 코드 생성
		market = f'KRW-{coin_symbol}'
		
		# 시장가 매도 주문
		result = place_upbit_order(market, 'ask', volume=coin_balance, ord_type='market')
		
		if result:
			log.info("매도 주문 성공 - 마켓: %s, 수량: %s", market, coin_balance)
			return True
		else:
			log.error("매도 주문 실패 - 마켓: %s", market)
			return False
	except Exception as e:
		log.error("매도 신호 실행 중 오류: %s", e)
		return False

def log_ta_signal_to_file(data: Dict[str, Any] | str, endpoint: str = "ta-signal") -> None:
	"""Log TradingView signal data to appropriate file based on endpoint.
	
	Args:
		data: Either JSON dict or string data from TradingView webhook
		endpoint: The endpoint name to determine the log file (ta-signal or ta-signal-test)
	"""
	try:
		# Create data directory if it doesn't exist
		data_dir = Path("data")
		data_dir.mkdir(exist_ok=True)
		
		
		# Create log file path based on endpoint
		log_file = data_dir / (endpoint + ".txt")

		# Get current timestamp
		timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		
		# Format the log entry
		if isinstance(data, dict):
			# JSON data - parse key fields
			strategy_name = data.get("strategy", {}).get("name", "Unknown")
			ticker = data.get("instrument", {}).get("ticker", "Unknown")
			action = data.get("order", {}).get("action", "Unknown")
			quantity = data.get("order", {}).get("quantity", "Unknown")
			position_size = data.get("position", {}).get("new_size", "Unknown")
			
			log_entry = f"[{timestamp}] JSON | Strategy: {strategy_name} | Ticker: {ticker} | Action: {action} | Qty: {quantity} | Position: {position_size} | Raw: {json.dumps(data, ensure_ascii=False)}"
		else:
			# Plain text data
			log_entry = f"[{timestamp}] TEXT | Data: {data}"
		
		# Append to file
		with open(log_file, "a", encoding="utf-8") as f:
			f.write(log_entry + "\n")
			
		log.info("Signal logged to %s", log_file)
		
	except Exception as e:
		log.error("Failed to log signal to file: %s", e)

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
			log_ta_signal_to_file(payload, "ta-signal-test")
		else:
			log.info("[TA-TEST] Text payload: %s", text_body)
			print("[TA-TEST] Text payload:", text_body)
			# Log to file
			log_ta_signal_to_file(text_body or "", "ta-signal-test")

		return jsonify({"status": "ok"}), 200
	except Exception as e:
		log.exception("Error handling /ta-signal-test: %s", e)
		return jsonify({"status": "error", "message": str(e)}), 500

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
			log_ta_signal_to_file(payload, "ta-signal")
			
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
					success = execute_buy_signal(ticker)
					if success:
						return jsonify({"status": "ok", "message": f"Buy order executed for {ticker}"}), 200
					else:
						return jsonify({"status": "error", "message": f"Buy order failed for {ticker}"}), 500
				
				elif action == "sell":
					success = execute_sell_signal(ticker)
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
			log_ta_signal_to_file(text_body or "", "ta-signal")

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
		balances = get_upbit_balances()
		total_balance = calculate_total_balance()
		
		return jsonify({
			"status": "ok", 
			"balances": balances,
			"total_balance_krw": total_balance
		}), 200
	except Exception as e:
		log.error("잔고 조회 테스트 중 오류: %s", e)
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
	# 로깅 설정 개선 - 파일과 콘솔 모두에 로그 출력
	if not logging.getLogger().handlers:
		# 로그 디렉토리 생성
		log_dir = Path("logs")
		log_dir.mkdir(exist_ok=True)
		
		# 로그 파일 경로
		log_file = log_dir / f"server_{datetime.now().strftime('%Y%m%d')}.log"
		
		# 로깅 포맷 설정
		formatter = logging.Formatter(
			'%(asctime)s - %(name)s - %(levelname)s - %(message)s'
		)
		
		# 파일 핸들러 (로그 파일에 저장)
		file_handler = logging.FileHandler(log_file, encoding='utf-8')
		file_handler.setFormatter(formatter)
		file_handler.setLevel(logging.INFO)
		
		# 콘솔 핸들러 (터미널에 출력)
		console_handler = logging.StreamHandler()
		console_handler.setFormatter(formatter)
		console_handler.setLevel(logging.INFO)
		
		# 루트 로거에 핸들러 추가
		root_logger = logging.getLogger()
		root_logger.setLevel(logging.INFO)
		root_logger.addHandler(file_handler)
		root_logger.addHandler(console_handler)
		
		log.info("로깅이 설정되었습니다. 로그 파일: %s", log_file)

	# 업비트 API 키 로드
	read_upbit_keys()

	ssl_context = _get_ssl_context()
	scheme = "HTTPS" if ssl_context else "HTTP"
	log.info("Starting %s server on %s:%s", scheme, host, port)
	print(f"Starting {scheme} server on {host}:{port}")

	# Note: For production, consider a WSGI server (gunicorn, waitress) behind a reverse proxy.
	app.run(host=host, port=port, debug=debug, ssl_context=ssl_context, use_reloader=False)


__all__ = ["run_server", "app"]

