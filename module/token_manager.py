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
    tokens = os.path.normpath(f.read().strip())

# 모의투자, 실전투자 구
INVEST_TYPE = "VIRT"    # 모의투자
# INVEST_TYPE = "REAL" # 실전투자

APP_KEY = keys[INVEST_TYPE]["APP_KEY"]
APP_SECRET = keys[INVEST_TYPE]["APP_SECRET"]
ACCESS_TOKEN = ""
URL_BASE = keys[INVEST_TYPE]["URL_BASE"]


def get_keys():
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
    ACCESS_TOKEN = ""
    URL_BASE = keys[INVEST_TYPE]["URL_BASE"]

# 토큰 발급 받아 저장 (토큰값, 토큰 유효시간,1일, 6시간 이내 발급신청시는 기존 토큰값과 동일, 발급시 알림톡 발송)
def save_token(my_token, my_expired):
    valid_date = datetime.strptime(my_expired, '%Y-%m-%d %H:%M:%S')
    # print('Save token date: ', valid_date)
    with open(token_tmp, 'w', encoding='utf-8') as f:
        f.write(f'token: {my_token}\n')
        f.write(f'valid-date: {valid_date}\n')


# 토큰 확인 (토큰값, 토큰 유효시간_1일, 6시간 이내 발급신청시는 기존 토큰값과 동일, 발급시 알림톡 발송)
def read_token():
    try:
        # 토큰이 저장된 파일 읽기
        with open(token_tmp, encoding='UTF-8') as f:
            tkg_tmp = yaml.load(f, Loader=yaml.FullLoader)

        # 토큰 만료 일,시간
        exp_dt = datetime.strftime(tkg_tmp['valid-date'], '%Y-%m-%d %H:%M:%S')
        # 현재일자,시간
        now_dt = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

        # print('expire dt: ', exp_dt, ' vs now dt:', now_dt)
        # 저장된 토큰 만료일자 체크 (만료일시 > 현재일시 인경우 보관 토큰 리턴)
        if exp_dt > now_dt:
            return tkg_tmp['token']
        else:
            # print('Need new token: ', tkg_tmp['valid-date'])
            return None
    except Exception as e:
        # print('read token error: ', e)
        return None

# 토큰 유효시간 체크해서 만료된 토큰이면 재발급처리
def _getBaseHeader():
    if _autoReAuth: reAuth()
    return copy.deepcopy(_base_headers)