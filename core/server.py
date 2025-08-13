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

# 마켓 정보 캐시 (서버 시작 시 한 번만 로드)
MARKET_INFO_CACHE = {}

# 매매 전략 설정
MAX_POSITION_RATIO = 0.2  # 각 종목 최대 비중 (20%)
MIN_ORDER_AMOUNT = 5000   # 최소 주문 금액 (원)
MIN_SELL_VALUE = 1000     # 최소 매도 가치 (원)

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

def load_upbit_markets():
	"""업비트 마켓 정보를 로드하고 캐시에 저장"""
	global MARKET_INFO_CACHE
	try:
		url = "https://api.upbit.com/v1/market/all?is_details=true"
		headers = {"accept": "application/json"}
		
		response = requests.get(url, headers=headers)
		if response.status_code == 200:
			markets = response.json()
			
			# 심볼별로 마켓 정보를 매핑
			for market in markets:
				market_code = market['market']  # 예: KRW-BTC
				if market_code.startswith('KRW-'):
					symbol = market_code.replace('KRW-', '')  # BTC
					MARKET_INFO_CACHE[symbol.upper()] = {
						'market': market_code,
						'korean_name': market.get('korean_name', ''),
						'english_name': market.get('english_name', '')
					}
			
			log.info("업비트 마켓 정보 로드 완료: %d개 마켓", len(MARKET_INFO_CACHE))
			return True
		else:
			log.error("마켓 정보 로드 실패: %s", response.text)
			return False
	except Exception as e:
		log.error("마켓 정보 로드 중 오류: %s", e)
		return False

def find_market_by_ticker(ticker):
	"""티커 심볼로 업비트 마켓 코드 찾기"""
	ticker_upper = ticker.upper()
	
	# 이미 KRW- 형태인 경우
	if ticker_upper.startswith('KRW-'):
		return ticker_upper
	
	# 캐시에서 찾기
	if ticker_upper in MARKET_INFO_CACHE:
		market_info = MARKET_INFO_CACHE[ticker_upper]
		log.info("티커 %s -> 마켓 %s (%s)", ticker, market_info['market'], market_info['korean_name'])
		return market_info['market']
	
	# 찾지 못한 경우
	log.warning("티커 '%s'에 해당하는 업비트 마켓을 찾을 수 없습니다.", ticker)
	log.info("지원 가능한 티커: %s", list(MARKET_INFO_CACHE.keys())[:10])  # 처음 10개만 표시
	return None

def get_available_tickers():
	"""사용 가능한 티커 목록 반환"""
	return list(MARKET_INFO_CACHE.keys())

def make_upbit_token(query_params=None):
	"""업비트 JWT 토큰 생성"""
	try:
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
		
		# PyJWT 2.0+ 호환성을 위한 수정
		jwt_token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
		
		# PyJWT 2.0+에서는 문자열을 반환하므로 추가 처리 불필요
		if isinstance(jwt_token, bytes):
			jwt_token = jwt_token.decode('utf-8')
			
		return f'Bearer {jwt_token}'
	except Exception as e:
		log.error("JWT 토큰 생성 중 오류: %s", e)
		return None

def get_upbit_balances():
	"""업비트 잔고 조회"""
	try:
		url = 'https://api.upbit.com/v1/accounts'
		token = make_upbit_token()
		if not token:
			log.error("JWT 토큰 생성 실패")
			return None
			
		headers = {'Authorization': token}
		
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
		}
		
		if side == 'bid':
			# 매수: 업비트에서는 시장가 매수 시 ord_type을 'price'로 설정
			params['ord_type'] = 'price'
			if price:
				params['price'] = str(int(price))
		elif side == 'ask':
			# 매도: 시장가 매도 시 ord_type을 'market'으로 설정
			params['ord_type'] = 'market'
			if volume:
				params['volume'] = str(volume)
		
		log.info("주문 파라미터: %s", params)
		
		token = make_upbit_token(params)
		if not token:
			log.error("JWT 토큰 생성 실패 - 주문 취소")
			return None
			
		headers = {'Authorization': token}
		
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
	"""매수 신호 실행 - 해당 종목이 전체 자산의 20%를 넘지 않도록 매수"""
	try:
		# 티커로 정확한 마켓 코드 찾기
		market = find_market_by_ticker(ticker)
		if not market:
			log.error("매수 실패: 티커 '%s'에 해당하는 마켓을 찾을 수 없습니다.", ticker)
			return False
		
		# 코인 심볼 추출
		coin_symbol = market.replace('KRW-', '')
		
		# 전체 자산 계산
		total_balance = calculate_total_balance()
		target_percentage = MAX_POSITION_RATIO  # 설정된 최대 비중 사용
		target_amount = total_balance * target_percentage
		
		log.info("전체 자산: %s원, 목표 비중: %s%% (%s원)", total_balance, target_percentage*100, target_amount)
		
		# 현재 해당 코인 보유량 확인
		balances = get_upbit_balances()
		current_coin_balance = 0
		current_coin_value = 0
		
		if balances:
			for balance in balances:
				if balance['currency'] == coin_symbol:
					current_coin_balance = float(balance['balance'])
					break
		
		# 현재 코인 가치 계산
		if current_coin_balance > 0:
			current_price = get_current_price(market)
			if current_price:
				current_coin_value = current_coin_balance * current_price
				log.info("현재 %s 보유량: %s개, 가치: %s원", coin_symbol, current_coin_balance, current_coin_value)
			else:
				log.error("현재가 조회 실패")
				return False
		else:
			log.info("현재 %s 보유량: 0개", coin_symbol)
		
		# 추가로 매수할 수 있는 금액 계산
		available_buy_amount = target_amount - current_coin_value
		
		if available_buy_amount <= 0:
			log.warning("이미 %s가 목표 비중(%s%%)을 달성했습니다. 현재 가치: %s원, 목표: %s원", 
					   coin_symbol, target_percentage*100, current_coin_value, target_amount)
			return False
		
		# 업비트 최소 주문 금액 확인
		if available_buy_amount < MIN_ORDER_AMOUNT:
			log.warning("매수 가능 금액이 최소 주문 금액보다 작습니다: %s원 (최소: %s원)", 
					   available_buy_amount, MIN_ORDER_AMOUNT)
			return False
		
		# 주문 금액을 원 단위로 반올림
		buy_amount = round(available_buy_amount)
		
		log.info("매수 신호 처리 - 티커: %s, 마켓: %s", ticker, market)
		log.info("현재 보유 가치: %s원, 목표 가치: %s원, 매수 금액: %s원", 
				current_coin_value, target_amount, buy_amount)
		
		# 시장가 매수 주문 (업비트에서는 ord_type='price' 사용)
		result = place_upbit_order(market, 'bid', price=buy_amount)
		
		if result:
			log.info("매수 주문 성공 - 마켓: %s, 금액: %s원", market, buy_amount)
			log.info("매수 후 예상 %s 가치: %s원 (전체 자산 대비 %s%%)", 
					coin_symbol, current_coin_value + buy_amount, 
					((current_coin_value + buy_amount) / total_balance) * 100)
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
		# 티커로 정확한 마켓 코드 찾기
		market = find_market_by_ticker(ticker)
		if not market:
			log.error("매도 실패: 티커 '%s'에 해당하는 마켓을 찾을 수 없습니다.", ticker)
			return False
		
		# 코인 심볼 추출 (KRW- 제거)
		coin_symbol = market.replace('KRW-', '')
		
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
			log.warning("매도할 %s 코인이 없습니다. (잔고: %s)", coin_symbol, coin_balance)
			return False
		
		# 최소 매도 수량 확인 (매우 작은 수량은 매도 불가)
		current_price = get_current_price(market)
		if current_price:
			estimated_value = coin_balance * current_price
			if estimated_value < MIN_SELL_VALUE:  # 설정된 최소 매도 가치 사용
				log.warning("매도 예상 금액이 너무 작습니다: %s원 (수량: %s %s, 최소: %s원)", 
						   estimated_value, coin_balance, coin_symbol, MIN_SELL_VALUE)
				return False
		
		log.info("매도 신호 처리 - 티커: %s, 마켓: %s, 수량: %s", ticker, market, coin_balance)
		
		# 시장가 매도 주문 (업비트에서는 ord_type='market' 사용)
		result = place_upbit_order(market, 'ask', volume=coin_balance)
		
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

@app.route("/markets", methods=["GET"])
def get_markets():
	"""지원 가능한 마켓 및 티커 목록 조회"""
	try:
		available_tickers = get_available_tickers()
		market_details = {}
		
		# 상위 20개 주요 코인만 상세 정보 포함
		major_tickers = ['BTC', 'ETH', 'XRP', 'ADA', 'DOT', 'LINK', 'LTC', 'BCH', 'EOS', 'TRX', 
						'ETC', 'ATOM', 'BAT', 'ENJ', 'KNC', 'MANA', 'SAND', 'AXS', 'CHZ', 'FLOW']
		
		for ticker in major_tickers:
			if ticker in MARKET_INFO_CACHE:
				market_details[ticker] = MARKET_INFO_CACHE[ticker]
		
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
		return jsonify({
			"status": "ok",
			"config": {
				"max_position_ratio": MAX_POSITION_RATIO,
				"max_position_percentage": f"{MAX_POSITION_RATIO * 100}%",
				"min_order_amount": MIN_ORDER_AMOUNT,
				"min_sell_value": MIN_SELL_VALUE
			},
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
	
	# 업비트 마켓 정보 로드
	log.info("업비트 마켓 정보를 로드 중입니다...")
	if load_upbit_markets():
		log.info("마켓 정보 로드 완료. 지원 가능한 티커 수: %d", len(MARKET_INFO_CACHE))
	else:
		log.warning("마켓 정보 로드 실패. 티커 매칭이 제한될 수 있습니다.")

	ssl_context = _get_ssl_context()
	scheme = "HTTPS" if ssl_context else "HTTP"
	log.info("Starting %s server on %s:%s", scheme, host, port)
	print(f"Starting {scheme} server on {host}:{port}")

	# Note: For production, consider a WSGI server (gunicorn, waitress) behind a reverse proxy.
	app.run(host=host, port=port, debug=debug, ssl_context=ssl_context, use_reloader=False)


__all__ = ["run_server", "app"]

