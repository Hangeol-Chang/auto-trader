# 키,토큰 관리 모듈

import os
import json
import requests
import copy
import yaml
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

APP_KEY = keys[INVEST_TYPE]["APP_KEY"]
APP_SECRET = keys[INVEST_TYPE]["APP_SECRET"]
ACCESS_TOKEN = tokens[INVEST_TYPE]["APP_TOKEN"]

URL_BASE = keys[INVEST_TYPE]["URL_BASE"]

def auth_validate():
    # acces_time을 검사해서, 5시간 이상 지났으면 재발급
    token_expire_time = tokens[INVEST_TYPE]["TOKEN_EXPIRE_TIME"]
    if not token_expire_time:
        # 토큰 재발급
        auth()
    else:
        token_expire_time = datetime.strptime(token_expire_time, '%Y-%m-%d %H:%M:%S')

        now = datetime.now()
        if now >= token_expire_time :
            # 토큰 재발급
            auth()
        else:
            # print(f"토큰 유효시간 확인: {token_expire_time} (현재시간: {now}) - 유효합니다.\n")
            pass

def auth():
    # print(f"인증 시작 | \nAPP_KEY: {APP_KEY} | \nAPP_SECRET: {APP_SECRET} | \nURL_BASE: {URL_BASE}")
    headers = {"content-type":"application/json"}
    body = {
        "grant_type":"client_credentials",
        "appkey":APP_KEY, 
        "appsecret":APP_SECRET
        }
    PATH = "oauth2/tokenP"
    URL = f"{URL_BASE}/{PATH}"
    res = requests.post(URL, headers=headers, data=json.dumps(body))
    
    global ACCESS_TOKEN
    # print(res.json())
    ACCESS_TOKEN = res.json()["access_token"]

    # 토큰, 토큰 시간 저장
    my_token = res.json()["access_token"]
    tokens[INVEST_TYPE]["APP_TOKEN"] = my_token
    tokens[INVEST_TYPE]["TOKEN_EXPIRE_TIME"] = res.json()["access_token_token_expired"]

    with open(token_path, 'w') as f:
        json.dump(tokens, f)


def get_keys():
    auth_validate()  # Ensure the token is valid before returning keys
    
    return {
        "APP_KEY": APP_KEY,
        "APP_SECRET": APP_SECRET,
        "ACCESS_TOKEN": ACCESS_TOKEN,
        "URL_BASE": URL_BASE
    }

def change_invest_type(invest_type):
    global INVEST_TYPE, APP_KEY, APP_SECRET, ACCESS_TOKEN, URL_BASE
    if INVEST_TYPE not in keys:
        raise ValueError(f"Invalid invest type: {invest_type}. Must be one of {list(keys.keys())}.")
    
    INVEST_TYPE = invest_type

    APP_KEY = keys[INVEST_TYPE]["APP_KEY"]
    APP_SECRET = keys[INVEST_TYPE]["APP_SECRET"]
    ACCESS_TOKEN = tokens[INVEST_TYPE]["APP_TOKEN"]
    URL_BASE = keys[INVEST_TYPE]["URL_BASE"]

    auth_validate()  # Validate the token after changing invest type
    
if __name__ == "__main__" :
    auth_validate()