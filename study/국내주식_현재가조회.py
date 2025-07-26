import requests
import json
import os


# 현재 스크립트 파일의 디렉토리 경로를 가져옵니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
# ../private/keys.json 파일의 절대 경로를 생성합니다.
keys_path = os.path.join(current_dir, '..', 'private', 'keys.json')
# 정규화된 경로로 변환하여 '..' 부분을 처리합니다.
keys_path = os.path.normpath(keys_path)

# 키 파일에서 API 키 정보를 읽어옵니다.
with open(keys_path, 'r') as f:
    keys = json.load(f)

# 모의투자, 실전투자 구
INVEST_TYPE = "VIRT"    # 모의투자
# INVEST_TYPE = "REAL" # 실전투자

APP_KEY = keys[INVEST_TYPE]["APP_KEY"]
APP_SECRET = keys[INVEST_TYPE]["APP_SECRET"]
ACCESS_TOKEN = ""
URL_BASE = keys[INVEST_TYPE]["URL_BASE"]

# Auth
def auth():
    print(f"인증 시작 | \nAPP_KEY: {APP_KEY} | \nAPP_SECRET: {APP_SECRET} | \nURL_BASE: {URL_BASE}")
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
    print(res.json())
    ACCESS_TOKEN = res.json()["access_token"]

# 주식현재가 시세
def get_current_price(stock_no):
    PATH = "uapi/domestic-stock/v1/quotations/inquire-price"
    URL = f"{URL_BASE}/{PATH}"

    # 헤더 설정
    print(f"REQUEST | \nAPP_KEY: {APP_KEY} | \nAPP_SECRET: {APP_SECRET} | \nURL_BASE: {URL_BASE}")

    if not ACCESS_TOKEN:
        auth()

    headers = {"Content-Type":"application/json", 
            "authorization": f"Bearer {ACCESS_TOKEN}",
            "appKey":APP_KEY,
            "appSecret":APP_SECRET,
            "tr_id":"FHKST01010100"}

    params = {
        "fid_cond_mrkt_div_code":"J",
        "fid_input_iscd": stock_no
    }

    # 호출
    res = requests.get(URL, headers=headers, params=params)

    if res.status_code == 200 and res.json()["rt_cd"] == "0" :
        return(res.json())
    # 토큰 만료 시
    elif res.status_code == 200 and res.json()["msg_cd"] == "EGW00123" :
        auth()
        get_current_price(stock_no)
    else:
        print("Error Code : " + str(res.status_code) + " | " + res.text)
        return None

print(get_current_price("005930"))