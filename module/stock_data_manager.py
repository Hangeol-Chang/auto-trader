'''
    TODO
    - 전체 데이터 검색에 대해, 로컬 db를 먼저 뒤져보고 없으면 가져와야 함.
    - 그리고 가져온 데이터는 무조건 저장해둘 것.
'''

import pandas as pd
from datetime import datetime, timedelta
import module.kis_fetcher as kis_fetcher



##############################################################################################
# [국내주식] 기본시세 > 주식현재가 일자별  (최근 30일만 조회)
# 주식현재가 일자별 API입니다. 일/주/월별 주가를 확인할 수 있으며 최근 30일(주,별)로 제한되어 있습니다.
##############################################################################################
# 주식현재가 일자별 Object를 DataFrame 으로 반환
# Input: None (Option) 상세 Input값 변경이 필요한 경우 API문서 참조
# Output: DataFrame (Option) output
def get_daily_price(div_code="J", itm_no="", period_code="D", adj_prc_code="1", tr_cont="", FK100="", NK100="", dataframe=None):  # [국내주식] 기본시세 > 주식현재가 일자별
    url = '/uapi/domestic-stock/v1/quotations/inquire-daily-price'
    tr_id = "FHKST01010400"  # 주식현재가 일자별

    params = {
        "FID_COND_MRKT_DIV_CODE": div_code, # 시장 분류 코드  J : 주식/ETF/ETN, W: ELW
        "FID_INPUT_ISCD": itm_no,           # 종목번호 (6자리) ETN의 경우, Q로 시작 (EX. Q500001)
        "FID_PERIOD_DIV_CODE": period_code, # 기간분류코드 D : (일)최근 30거래일, W : (주)최근 30주, M : (월)최근 30개월
        "FID_ORG_ADJ_PRC": adj_prc_code     # 0 : 수정주가반영, 1 : 수정주가미반영 * 수정주가는 액면분할/액면병합 등 권리 발생 시 과거 시세를 현재 주가에 맞게 보정한 가격
    }
    res = kis_fetcher._url_fetch(url, tr_id, tr_cont, params)

    # print(res.getBody())  # 오류 원인 확인 필요시 사용
    # Assuming 'output' is a dictionary that you want to convert to a DataFrame
    current_data = pd.DataFrame(res.getBody().output)  # getBody() kis_auth.py 존재

    dataframe = current_data

    return dataframe

##############################################################################################
# [국내주식] 기본시세 > 국내주식기간별시세(일/주/월/년)
# 국내주식기간별시세(일/주/월/년) API입니다.
# 실전계좌/모의계좌의 경우, 한 번의 호출에 최대 100건까지 확인 가능합니다.
##############################################################################################
# 국내주식기간별시세(일/주/월/년) Object를 DataFrame 으로 반환
# Input: None (Option) 상세 Input값 변경이 필요한 경우 API문서 참조
# Output: DataFrame (Option) output
def get_itempricechart_1(
    div_code="J",   # 시장 분류 코드 J: 주식/ETF/ETN, W: ELW
    itm_no="",      # 종목번호 (6자리) ETN의 경우, Q로 시작 (EX. Q500001)
    tr_cont="",     # 트랜잭션 내용 (선택사항)
    start_date = None,
    end_date = None,
    period_code="D", 
    adj_prc="1", 
    dataframe=None
) :
    url = '/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice'
    tr_id = "FHKST03010100"  # 주식현재가 회원사

    if start_date is None:
        start_date = (datetime.now()-timedelta(days=14)).strftime("%Y%m%d")   # 시작일자 값이 없으면 현재일자
    if  end_date is None:
        end_date  = datetime.today().strftime("%Y%m%d")   # 종료일자 값이 없으면 현재일자

    print(start_date)
    print(end_date)
    params = {
        "FID_COND_MRKT_DIV_CODE": div_code, # 시장 분류 코드  J : 주식/ETF/ETN, W: ELW
        "FID_INPUT_ISCD": itm_no,           # 종목번호 (6자리) ETN의 경우, Q로 시작 (EX. Q500001)
        "FID_INPUT_DATE_1": start_date,   # 입력 날짜 (시작) 조회 시작일자 (ex. 20220501)
        "FID_INPUT_DATE_2": end_date,    # 입력 날짜 (종료) 조회 종료일자 (ex. 20220530)
        "FID_PERIOD_DIV_CODE": period_code, # 기간분류코드 D:일봉, W:주봉, M:월봉, Y:년봉
        "FID_ORG_ADJ_PRC": adj_prc          # 수정주가 0:수정주가 1:원주가
    }
    res = kis_fetcher._url_fetch(url, tr_id, tr_cont, params)

    # output1: 현재가 정보 (실시간 상태)
    current_data = pd.DataFrame(res.getBody().output1, index=[0])  # 현재가 정보

    dataframe = current_data
    return dataframe

def get_itempricechart_2(
        div_code="J",   # 시장 분류 코드 J: 주식/ETF/ETN, W: ELW
        itm_no="",      # 종목번호 (6자리) ETN의 경우, Q로 시작 (EX. Q500001)
        tr_cont="",     # 트랜잭션 내용 (선택사항)
        start_date=None, 
        end_date=None, 
        period_code="D", 
        adj_prc="1", 
        dataframe=None
):  
    # [국내주식] 기본시세 > 국내주식기간별시세(일/주/월/년)

    url = '/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice'
    tr_id = "FHKST03010100"  # 주식현재가 회원사

    if start_date is None:
        start_date = (datetime.now()-timedelta(days=14)).strftime("%Y%m%d")   # 시작일자 값이 없으면 2주 전 일자
    if  end_date is None:
        end_date  = datetime.today().strftime("%Y%m%d")   # 종료일자 값이 없으면 현재일자

    params = {
        "FID_COND_MRKT_DIV_CODE": div_code, # 시장 분류 코드  J : 주식/ETF/ETN, W: ELW
        "FID_INPUT_ISCD": itm_no,           # 종목번호 (6자리) ETN의 경우, Q로 시작 (EX. Q500001)
        "FID_INPUT_DATE_1": start_date,   # 입력 날짜 (시작) 조회 시작일자 (ex. 20220501)
        "FID_INPUT_DATE_2": end_date,    # 입력 날짜 (종료) 조회 종료일자 (ex. 20220530)
        "FID_PERIOD_DIV_CODE": period_code, # 기간분류코드 D:일봉, W:주봉, M:월봉, Y:년봉
        "FID_ORG_ADJ_PRC": adj_prc          # 수정주가 0:수정주가 1:원주가
    }
    res = kis_fetcher._url_fetch(url, tr_id, tr_cont, params)

    # output2: 기간별 OHLCV 히스토리 데이터 (차트 분석용)
    current_data = pd.DataFrame(res.getBody().output2)  # 기간별 일봉 데이터

    dataframe = current_data

    return dataframe