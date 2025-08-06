import multiprocessing
import time
import logging

import jwt
import uuid
import requests
import json

from core import visualizer, trader
from module import stock_data_manager as sd_m
from module import stock_data_manager_ws as sd_m_ws
from module import token_manager as tm

# INVEST_TYPE = "PROD"  # 실전투자
INVEST_TYPE = "VPS"    # 모의투자

# if __name__ == "__main__":
    # token_manager.auth_validate(invest_type=INVEST_TYPE)
    # tm.auth_ws_validate(invest_type=INVEST_TYPE)

    # print("init")
    # kws = tm.KISWebSocket(api_url="/tryitout")
    # print("init done")
    # kws.subscribe(request=sd_m_ws.asking_price_krx, data=["005930", "000660"])
    # print("subscribed")
    
    # def on_result(ws, tr_id, result, data_info):
    #     print("result:", result)
    #     print("data_info:", data_info)

    # # 장 마감 시간에는 데이터 안들어옴...
    # kws.start(on_result=on_result)


    # 코인 거래 테스트


# ▼ 발급받은 키를 입력하세요
ACCESS_KEY = ''
SECRET_KEY = ''

def read_token():
    with open('./private/keys.json', 'r') as f:
        keys = json.load(f)
        global ACCESS_KEY, SECRET_KEY
        ACCESS_KEY = keys['COIN'][0]['APP_KEY']
        SECRET_KEY = keys['COIN'][0]['APP_SECRET']

# ▼ JWT 토큰 생성
def make_token():
    payload = {
        'access_key': ACCESS_KEY,
        'nonce': str(uuid.uuid4()),
    }
    jwt_token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    authorization_token = f'Bearer {jwt_token}'
    return authorization_token

# ▼ 잔고 조회 요청
def get_balances():
    url = 'https://api.upbit.com/v1/accounts'
    headers = {
        'Authorization': make_token(),
    }
    print("Requesting balances with headers:", headers)
    res = requests.get(url, headers=headers)
    print(res.status_code, res.text)
    return res.json()

def get_all_market():
    url = "https://api.upbit.com/v1/market/all?is_details=true"

    headers = {"accept": "application/json"}

    res = requests.get(url, headers=headers)
    print("Requesting all market data with headers:", headers)
    print(res.status_code, res.text)

    return res.json()

def get_market_price_minute(market):
    url = "https://api.upbit.com/v1/candles/minutes/1"
    params = {
        'market': market,  # 마켓 코드
        'count': 1,
        'to': '2024-10-01 00:00:00'
    }  
    headers = {"accept": "application/json"}

    response = requests.get(url, params=params, headers=headers)
    print(response.text)
    if response.status_code == 200:
        data = response.json()
        print("Market price data:", data)
    else:
        print("Failed to retrieve market price data")
    return response.json()

def get_market_price_second(market):
    url = "https://api.upbit.com/v1/candles/seconds"
    params = {
        'market': market,
        'count': 1,
        'to': '2024-10-01 00:00:00'
    }  
    headers = {"accept": "application/json"}

    response = requests.get(url, params=params, headers=headers)

    print(response.text)
    if response.status_code == 200:
        data = response.json()
        print("Market price data:", data)
    else:
        print("Failed to retrieve market price data")
    return response.json()

def get_current_price(markets):
    market_str = ','.join(markets)
    server_url = "https://api.upbit.com"
    params = {
        "markets": market_str
    }

    res = requests.get(server_url + "/v1/ticker", params=params)
    print(res.json())

# ▼ 실행
if __name__ == "__main__":
    read_token()
    balances = get_balances()
    for b in balances:
        print(f"{b['currency']}: {b['balance']} (locked: {b['locked']})")


    # 시세 조회.

    get_all_market()
    # {
    #     "market": "KRW-BTC",
    #     "korean_name": "비트코인",
    #     "english_name": "Bitcoin",
    #     "market_event": {
    #     "warning": false,
    #     "caution": {
    #         "PRICE_FLUCTUATIONS": false,
    #         "TRADING_VOLUME_SOARING": false,
    #         "DEPOSIT_AMOUNT_SOARING": true,
    #         "GLOBAL_PRICE_DIFFERENCES": false,
    #         "CONCENTRATION_OF_SMALL_ACCOUNTS": false
    #     }
    # }

    """
        - PRICE_FLUCTUATIONS: 가격 급등락 경보 발령 여부
        - TRADING_VOLUME_SOARING: 거래량 급등 경보 발령 여부
        - DEPOSIT_AMOUNT_SOARING: 입금량 급등 경보 발령 여부
        - GLOBAL_PRICE_DIFFERENCES: 가격 차이 경보 발령 여부
        - CONCENTRATION_OF_SMALL_ACCOUNTS: 소수 계정 집중 경보 발령 여부
    """

    # 시세 조회 예시

    # 초단위 조회
    get_market_price_second("KRW-BTC")
    # 분단위 조회
    get_market_price_minute("KRW-BTC")

    """
        market	종목 코드	String
        candle_date_time_utc	캔들 기준 시각(UTC 기준)
        포맷: yyyy-MM-dd'T'HH:mm:ss	String
        candle_date_time_kst	캔들 기준 시각(KST 기준)
        포맷: yyyy-MM-dd'T'HH:mm:ss	String
        opening_price	시가	Double
        high_price	고가	Double
        low_price	저가	Double
        trade_price	종가	Double
        timestamp	마지막 틱이 저장된 시각	Long
        candle_acc_trade_price	누적 거래 금액	Double
        candle_acc_trade_volume	누적 거래량	Double
    """

    # 현재가 스냅샷 -> 여러 개의 종목을 가져올 수 있음.
    get_current_price(["KRW-BTC", "KRW-ETH", "KRW-XRP"])
    """
        market	종목 구분 코드	String
        trade_date	최근 거래 일자(UTC)
        포맷: yyyyMMdd	String
        trade_time	최근 거래 시각(UTC)
        포맷: HHmmss	String
        trade_date_kst	최근 거래 일자(KST)
        포맷: yyyyMMdd	String
        trade_time_kst	최근 거래 시각(KST)
        포맷: HHmmss	String
        trade_timestamp	최근 거래 일시(UTC)
        포맷: Unix Timestamp	Long
        opening_price	시가	Double
        high_price	고가	Double
        low_price	저가	Double
        trade_price	종가(현재가)	Double
        prev_closing_price	전일 종가(UTC 0시 기준)	Double
        change	EVEN : 보합
        RISE : 상승
        FALL : 하락	String
        change_price	변화액의 절대값	Double
        change_rate	변화율의 절대값	Double
        signed_change_price	부호가 있는 변화액	Double
        signed_change_rate	부호가 있는 변화율	Double
        trade_volume	가장 최근 거래량	Double
        acc_trade_price	누적 거래대금(UTC 0시 기준)	Double
        acc_trade_price_24h	24시간 누적 거래대금	Double
        acc_trade_volume	누적 거래량(UTC 0시 기준)	Double
        acc_trade_volume_24h	24시간 누적 거래량	Double
        highest_52_week_price	52주 신고가	Double
        highest_52_week_date	52주 신고가 달성일
        포맷: yyyy-MM-dd	String
        lowest_52_week_price	52주 신저가	Double
        lowest_52_week_date	52주 신저가 달성일
        포맷: yyyy-MM-dd	String
        timestamp	타임스탬프	Long
    """