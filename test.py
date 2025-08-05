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
    res = requests.get(url, headers=headers)
    return res.json()

# ▼ 실행
if __name__ == "__main__":
    read_token()
    balances = get_balances()
    for b in balances:
        print(f"{b['currency']}: {b['balance']} (locked: {b['locked']})")
