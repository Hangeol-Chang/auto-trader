# 키,토큰 관리 모듈

'''
    TODO
    - 실시간 거래를 위한 WebsSocket 방식이 구현되어야 함.
'''

import os
import json
import requests
from datetime import datetime, timedelta
from collections import namedtuple

## common api
def _getResultObject(json_data):
    _tc_ = namedtuple("res", json_data.keys())

    return _tc_(**json_data)

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
    # print(body)
    PATH = "oauth2/tokenP"
    URL = f"{keys[invest_type][index]['URL_BASE']}/{PATH}"
    res = requests.post(URL, headers=headers, data=json.dumps(body))

    # 토큰, 토큰 시간 저장
    my_token = res.json()["access_token"]
    tokens[INVEST_TYPE][str(index)]["APP_TOKEN"] = my_token
    tokens[INVEST_TYPE][str(index)]["TOKEN_EXPIRE_TIME"] = res.json()["access_token_token_expired"]

    with open(token_path, 'w') as f:
        json.dump(tokens, f)

def auth_ws_validate(invest_type="VPS", index=0):
    # acces_time을 검사해서, 5시간 이상 지났으면 재발급
    token_expire_time = tokens[invest_type][str(index)]['WS_TOKEN_EXPIRE_TIME']
    if not token_expire_time:
        # 토큰 재발급
        auth_ws(invest_type, index)
    else:
        token_expire_time = datetime.strptime(token_expire_time, '%Y-%m-%d %H:%M:%S')
        
        now = datetime.now()
        if now >= token_expire_time :
            # 토큰 재발급
            auth(invest_type, index)
        else:
            # print(f"토큰 유효시간 확인: {token_expire_time} (현재시간: {now}) - 유효합니다.\n")
            pass

def auth_ws(invest_type="VPS", index=0):
    headers = {"content-type":"application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": keys[invest_type][index]["APP_KEY"],
        "secretkey": keys[invest_type][index]["APP_SECRET"]
    }

    PATH = "oauth2/Approval"
    URL = f"{keys[invest_type][index]['URL_BASE']}/{PATH}"

    res = requests.post(URL, data=json.dumps(body), headers=headers)  # 토큰 발급
    print("res : ", res, res.json(), res.status_code)

    rescode = res.status_code
    if rescode == 200:  # 토큰 정상 발급
        approval_key = _getResultObject(res.json()).approval_key
    else:
        print("Get Approval token fail!")
        return

    tokens[invest_type][str(index)]["WS_APPROVAL_KEY"] = approval_key
    tokens[invest_type][str(index)]["WS_TOKEN_EXPIRE_TIME"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + 60 * 60 * 24))  # 24시간 유효
    
    with open(token_path, 'w') as f:
        json.dump(tokens, f)


def get_keys(invest_type="VPS", index=0):
    auth_validate(invest_type, index)  # Ensure the token is valid before returning keys

    return {
        "APP_KEY": keys[invest_type][index]['APP_KEY'],
        "APP_SECRET": keys[invest_type][index]['APP_SECRET'],
        "ACCESS_TOKEN": tokens[invest_type][str(index)]['APP_TOKEN'],
        "WS_APPROVAL_KEY": tokens[invest_type][str(index)]['WS_APPROVAL_KEY'],        
        "URL_BASE": keys[invest_type][index]['URL_BASE']
    }

def change_invest_type(invest_type="VPS", index=0):
    global INVEST_TYPE
    if invest_type not in keys:
        raise ValueError(f"Invalid invest type: {invest_type}. Must be one of {list(keys.keys())}.")
    
    INVEST_TYPE = invest_type
    auth_validate(invest_type, index)  # Validate the token after changing invest type


#####################################################################
############## WebSocket 관련 코드 ###################################
#####################################################################

import asyncio
import websockets
import pandas as pd
from typing import Callable
from io import StringIO
import logging
from base64 import b64decode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import time

def aes_cbc_base64_dec(key, iv, cipher_text):
    if key is None or iv is None:
        raise AttributeError("key and iv cannot be None")

    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv.encode("utf-8"))
    return bytes.decode(unpad(cipher.decrypt(b64decode(cipher_text)), AES.block_size))


# iv, ekey, encrypt 는 각 기능 메소드 파일에 저장할 수 있도록 dict에서 return 하도록
def system_resp(data):
    isPingPong = False
    isUnSub = False
    isOk = False
    tr_msg = None
    tr_key = None
    encrypt, iv, ekey = None, None, None

    rdic = json.loads(data)

    tr_id = rdic["header"]["tr_id"]
    if tr_id != "PINGPONG":
        tr_key = rdic["header"]["tr_key"]
        encrypt = rdic["header"]["encrypt"]
    if rdic.get("body", None) is not None:
        isOk = True if rdic["body"]["rt_cd"] == "0" else False
        tr_msg = rdic["body"]["msg1"]
        # 복호화를 위한 key 를 추출
        if "output" in rdic["body"]:
            iv = rdic["body"]["output"]["iv"]
            ekey = rdic["body"]["output"]["key"]
        isUnSub = True if tr_msg[:5] == "UNSUB" else False
    else:
        isPingPong = True if tr_id == "PINGPONG" else False

    nt2 = namedtuple(
        "SysMsg",
        [
            "isOk",
            "tr_id",
            "tr_key",
            "isUnSub",
            "isPingPong",
            "tr_msg",
            "iv",
            "ekey",
            "encrypt",
        ],
    )
    d = {
        "isOk": isOk,
        "tr_id": tr_id,
        "tr_key": tr_key,
        "tr_msg": tr_msg,
        "isUnSub": isUnSub,
        "isPingPong": isPingPong,
        "iv": iv,
        "ekey": ekey,
        "encrypt": encrypt,
    }

    return nt2(**d)

#####
open_map: dict = {}

def add_open_map(
        name: str,
        request: Callable[[str, str, ...], tuple[dict, list[str]]],
        data: str | list[str],
        kwargs: dict = None,
):
    if open_map.get(name, None) is None:
        open_map[name] = {
            "func": request,
            "items": [],
            "kwargs": kwargs,
        }

    if type(data) is list:
        open_map[name]["items"] += data
    elif type(data) is str:
        open_map[name]["items"].append(data)

data_map: dict = {}

def add_data_map(
        tr_id: str,
        columns: list = None,
        encrypt: str = None,
        key: str = None,
        iv: str = None,
):
    if data_map.get(tr_id, None) is None:
        data_map[tr_id] = {"columns": [], "encrypt": False, "key": None, "iv": None}

    if columns is not None:
        data_map[tr_id]["columns"] = columns

    if encrypt is not None:
        data_map[tr_id]["encrypt"] = encrypt

    if key is not None:
        data_map[tr_id]["key"] = key

    if iv is not None:
        data_map[tr_id]["iv"] = iv


class KISWebSocket:
    base_url: str = ""
    api_url: str = ""
    on_result: Callable[
        [websockets.ClientConnection, str, pd.DataFrame, dict], None
    ] = None
    result_all_data: bool = False

    retry_count: int = 0
    amx_retries: int = 0

    # init
    def __init__(self, api_url: str, max_retries: int = 3):
        self.api_url = api_url
        self.max_retries = max_retries

    # private
    async def __subscriber(self, ws: websockets.ClientConnection):
        async for raw in ws:
            logging.info("received message >> %s" % raw)
            show_result = False

            df = pd.DataFrame()

            if raw[0] in ["0", "1"]:
                d1 = raw.split("|")
                if len(d1) < 4:
                    raise ValueError("data not found...")

                tr_id = d1[1]

                dm = data_map[tr_id]
                d = d1[3]
                if dm.get("encrypt", None) == "Y":
                    d = aes_cbc_base64_dec(dm["key"], dm["iv"], d)

                df = pd.read_csv(
                    StringIO(d), header=None, sep="^", names=dm["columns"], dtype=object
                )

                show_result = True

            else:
                rsp = system_resp(raw)

                tr_id = rsp.tr_id
                add_data_map(
                    tr_id=rsp.tr_id, encrypt=rsp.encrypt, key=rsp.ekey, iv=rsp.iv
                )

                if rsp.isPingPong:
                    print(f"### RECV [PINGPONG] [{raw}]")
                    await ws.pong(raw)
                    print(f"### SEND [PINGPONG] [{raw}]")

                if self.result_all_data:
                    show_result = True

            if show_result is True and self.on_result is not None:
                self.on_result(ws, tr_id, df, data_map[tr_id])

    async def __runner(self):
        if len(open_map.keys()) > 40:
            raise ValueError("Subscription's max is 40")

        url = f"{self.base_url}/{self.api_url}"

        while self.retry_count < self.max_retries:
            try:
                async with websockets.connect(url) as ws:
                    # request subscribe
                    for name, obj in open_map.items():
                        await self.send_multiple(
                            ws, obj["func"], "1", obj["items"], obj["kwargs"]
                        )

                    # subscriber
                    await asyncio.gather(
                        self.__subscriber(ws),
                    )
            except Exception as e:
                print("Connection exception >> ", e)
                self.retry_count += 1
                await asyncio.sleep(1)

    # func
    @classmethod
    async def send(
            cls,
            ws: websockets.ClientConnection,
            request: Callable[[str, str, ...], tuple[dict, list[str]]],
            tr_type: str,
            data: str,
            kwargs: dict = None,
    ):
        k = {} if kwargs is None else kwargs
        msg, columns = request(tr_type, data, **k)

        add_data_map(tr_id=msg["body"]["input"]["tr_id"], columns=columns)

        logging.info("send message >> %s" % json.dumps(msg))

        await ws.send(json.dumps(msg))
        time.sleep(0.1)  # 잠시 대기

    async def send_multiple(
            self,
            ws: websockets.ClientConnection,
            request: Callable[[str, str, ...], tuple[dict, list[str]]],
            tr_type: str,
            data: list | str,
            kwargs: dict = None,
    ):
        if type(data) is str:
            await self.send(ws, request, tr_type, data, kwargs)
        elif type(data) is list:
            for d in data:
                await self.send(ws, request, tr_type, d, kwargs)
        else:
            raise ValueError("data must be str or list")

    @classmethod
    def subscribe(
            cls,
            request: Callable[[str, str, ...], tuple[dict, list[str]]],
            data: list | str,
            kwargs: dict = None,
    ):
        add_open_map(request.__name__, request, data, kwargs)

    def unsubscribe(
            self,
            ws: websockets.ClientConnection,
            request: Callable[[str, str, ...], tuple[dict, list[str]]],
            data: list | str,
    ):
        self.send_multiple(ws, request, "2", data)

    # start
    def start(
            self,
            on_result: Callable[
                [websockets.ClientConnection, str, pd.DataFrame, dict], None
            ],
            result_all_data: bool = False,
    ):
        self.on_result = on_result
        self.result_all_data = result_all_data
        try:
            asyncio.run(self.__runner())
        except KeyboardInterrupt:
            print("Closing by KeyboardInterrupt")


### 테스트 실행부
if __name__ == "__main__" :
    auth_validate(invest_type=INVEST_TYPE, index=0)