# 키,토큰 관리 모듈

'''
    TODO
    - 실시간 거래를 위한 WebsSocket 방식이 구현되어야 함.
'''

import os
import json
import requests
from datetime import datetime, timedelta

# 파일 읽어오기
current_dir = os.path.dirname(os.path.abspath(__file__))
keys_path = os.path.join(current_dir, '..', 'private', 'keys.json')
keys_path = os.path.normpath(keys_path)

token_path = os.path.join(current_dir, '..', 'private', 'token.json')
token_path = os.path.normpath(token_path)

# 키 파일에서 API 키 정보를 읽어옵니다.
with open(keys_path, 'r') as f:
    keys = json.load(f)

with open(token_path, 'r') as f:
    tokens = json.load(f)

# 모의투자, 실전투자 구
# INVEST_TYPE = "PROD" # 실전투자
INVEST_TYPE = "VPS"    # 모의투자


def auth_validate(invest_type="VPS", index=0):
    # acces_time을 검사해서, 5시간 이상 지났으면 재발급
    token_expire_time = tokens[invest_type][str(index)]['TOKEN_EXPIRE_TIME']
    if not token_expire_time:
        # 토큰 재발급
        auth(invest_type, index)
    else:
        token_expire_time = datetime.strptime(token_expire_time, '%Y-%m-%d %H:%M:%S')

        now = datetime.now()
        if now >= token_expire_time :
            # 토큰 재발급
            auth(invest_type, index)
        else:
            # print(f"토큰 유효시간 확인: {token_expire_time} (현재시간: {now}) - 유효합니다.\n")
            pass

def auth(invest_type="VPS", index=0):
    # print(f"인증 시작 | \nAPP_KEY: {APP_KEY} | \nAPP_SECRET: {APP_SECRET} | \nURL_BASE: {URL_BASE}")
    headers = {"content-type":"application/json"}
    body = {
        "grant_type":"client_credentials",
        "appkey":keys[invest_type][index]["APP_KEY"], 
        "appsecret":keys[invest_type][index]["APP_SECRET"]
    }
    print(body)
    PATH = "oauth2/tokenP"
    URL = f"{keys[invest_type][index]['URL_BASE']}/{PATH}"
    res = requests.post(URL, headers=headers, data=json.dumps(body))

    # 토큰, 토큰 시간 저장
    my_token = res.json()["access_token"]
    tokens[INVEST_TYPE][str(index)]["APP_TOKEN"] = my_token
    tokens[INVEST_TYPE][str(index)]["TOKEN_EXPIRE_TIME"] = res.json()["access_token_token_expired"]

    with open(token_path, 'w') as f:
        json.dump(tokens, f)


def get_keys(invest_type="VPS", index=0):
    auth_validate(invest_type, index)  # Ensure the token is valid before returning keys

    return {
        "APP_KEY": keys[invest_type][index]['APP_KEY'],
        "APP_SECRET": keys[invest_type][index]['APP_SECRET'],
        "ACCESS_TOKEN": tokens[invest_type][str(index)]['APP_TOKEN'],
        "URL_BASE": keys[invest_type][index]['URL_BASE']
    }

def change_invest_type(invest_type="VPS", index=0):
    global INVEST_TYPE
    if invest_type not in keys:
        raise ValueError(f"Invalid invest type: {invest_type}. Must be one of {list(keys.keys())}.")
    
    INVEST_TYPE = invest_type
    auth_validate(invest_type, index)  # Validate the token after changing invest type

if __name__ == "__main__" :
    auth_validate(invest_type=INVEST_TYPE, index=0)