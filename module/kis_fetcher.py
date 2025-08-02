'''
# kis_fetcher.py
kis API 호출에 필요한 공통 함수들
'''
import copy
from collections import namedtuple
import module.token_manager as token_manager
import requests
import json

_DEBUG = False  # 디버그 모드 설정

# 기본 헤더값 정의
_base_headers = {
    "Content-Type": "application/json",
    "Accept": "text/plain",
    "charset": "UTF-8",
    'User-Agent': "AutoTrader/1.0 (Python)",

    "authorization" : "",
    "appkey": "" ,
    "appsecret": ""
}

global keys
def _getBaseHeader():
    keys = token_manager.get_keys()
    _base_headers["authorization"] = f"Bearer {keys['ACCESS_TOKEN']}"
    _base_headers["appkey"] = keys["APP_KEY"]
    _base_headers["appsecret"] = keys["APP_SECRET"]

    return copy.deepcopy(_base_headers), keys['URL_BASE']

# API 호출 응답에 필요한 처리 공통 함수
class APIResp:
    def __init__(self, resp):
        self._rescode = resp.status_code
        self._resp = resp
        self._header = self._setHeader()
        self._body = self._setBody()
        self._err_code = self._body.msg_cd
        self._err_message = self._body.msg1

    def getResCode(self):
        return self._rescode

    def _setHeader(self):
        fld = dict()
        for x in self._resp.headers.keys():
            if x.islower():
                fld[x] = self._resp.headers.get(x)
        _th_ = namedtuple('header', fld.keys())

        return _th_(**fld)

    def _setBody(self):
        _tb_ = namedtuple('body', self._resp.json().keys())

        return _tb_(**self._resp.json())

    def getHeader(self):
        return self._header

    def getBody(self):
        return self._body

    def getResponse(self):
        return self._resp

    def isOK(self):
        try:
            if (self.getBody().rt_cd == '0'):
                return True
            else:
                return False
        except:
            return False

    def getErrorCode(self):
        return self._err_code

    def getErrorMessage(self):
        return self._err_message

    def printAll(self):
        print("<Header>")
        for x in self.getHeader()._fields:
            print(f'\t-{x}: {getattr(self.getHeader(), x)}')
        print("<Body>")
        for x in self.getBody()._fields:
            print(f'\t-{x}: {getattr(self.getBody(), x)}')

    def printError(self, url):
        print('-------------------------------\nError in response: ', self.getResCode(), ' url=', url)
        print('rt_cd : ', self.getBody().rt_cd, '/ msg_cd : ',self.getErrorCode(), '/ msg1 : ',self.getErrorMessage())
        print('-------------------------------')

    # end of class APIResp

########### API call wrapping : API 호출 공통

def _url_fetch(api_url, ptr_id, tr_cont, params, appendHeaders=None, postFlag=False, hashFlag=True):
    headers, base_url = _getBaseHeader()  # 기본 header 값 정리
    url = f"{base_url}/{api_url}"


    # 추가 Header 설정
    tr_id = ptr_id
    if ptr_id[0] in ('T', 'J', 'C'):  # 실전투자용 TR id 체크
        if keys['INVEST_TYPE'] == 'VPS':    # 모의투자용 TR id로 변경
            tr_id = 'V' + ptr_id[1:]

    headers["tr_id"] = tr_id  # 트랜젝션 TR id
    headers["custtype"] = "P"  # 일반(개인고객,법인고객) "P", 제휴사 "B"
    headers["tr_cont"] = tr_cont  # 트랜젝션 TR id

# {'FID_COND_MRKT_DIV_CODE': 'N', 'FID_INPUT_ISCD': 'AAPL', 'FID_INPUT_DATE_1': '20230103', 'FID_INPUT_DATE_2': '20230410', 'FID_PERIOD_DIV_CODE': 'D'}
# {'FID_COND_MRKT_DIV_CODE': 'N', 'FID_INPUT_ISCD': 'AAPL', 'FID_INPUT_DATE_1': '20230101', 'FID_INPUT_DATE_2': '20231231', 'FID_PERIOD_DIV_CODE': 'D'}
    if appendHeaders is not None:
        if len(appendHeaders) > 0:
            for x in appendHeaders.keys():
                headers[x] = appendHeaders.get(x)

    if (_DEBUG):
        print("< Sending Info >")
        print(f"URL: {url}, TR: {tr_id}")
        print(f"<header>\n{headers}")
        print(f"<body>\n{params}")

    if (postFlag):
        #if (hashFlag): set_order_hash_key(headers, params)
        res = requests.post(url, headers=headers, data=json.dumps(params))
    else:
        res = requests.get(url, headers=headers, params=params)

    if res.status_code == 200:
        ar = APIResp(res)
        if (_DEBUG): ar.printAll()
        return ar
    else:
        print("Error Code : " + str(res.status_code) + " | " + res.text)
        return None

