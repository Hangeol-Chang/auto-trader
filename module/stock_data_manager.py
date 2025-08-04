'''
    RULES
    - column name은 무조건 소문자로 작성.
    - 이 파일 외부에서 column_name을 my_app의 것으로만 사용
    - 이 파일 외부에서 날짜는 YYYYMMDD 형식으로 사용

    TODO
    ** COLUMN name 변환?
    - 변환은 여기서 전부 처리해야 함.
    - 이 파일 외부에서는 my_app의 column name만 사용할 것임.
    
    ** CSV 파일 저장 규칙:
    - {종목번호}_{API명}_{기간코드}.csv 형태로 저장
    - get_itempricechart_1: {종목번호}_itemchartprice_current_{기간코드}.csv
    - get_itempricechart_2: {종목번호}_itemchartprice_history_{기간코드}.csv
    - 데이터는 data/stock_cache/ 디렉토리에 저장됨
'''

from unittest import result
import pandas as pd
import os
from datetime import datetime, timedelta
from pykrx import stock
import yfinance as yf
import time
import re

import module.kis_fetcher as kis_fetcher
import module.column_mapper as column_mapper
from module.common.db_manager import *

# 각 나라별 대표 종목 (거래일 조회용)
COUNTRY_REPRESENTATIVE_TICKERS = {
    'KR': '005930.KS',      # 삼성전자 (한국)
    'US': 'AAPL',           # Apple (미국)
    'JP': '7203.T',         # Toyota (일본)
    # 'CN': '000001.SS',      # 상해종합지수 ETF (중국)
    'HK': '0700.HK',        # Tencent (홍콩)
    # 'AU': 'CBA.AX',         # Commonwealth Bank (호주)
}

##############################################################################################
# 날짜 관련 로직
##############################################################################################
def get_country_code(ticker: str) -> str:
    ticker = ticker.upper().strip()

    # 접미사 기반 우선 판별
    suffix_map = {
        '.KS': 'KR',  # KOSPI
        '.KQ': 'KR',  # KOSDAQ
        '.T':  'JP',  # Tokyo
        '.HK': 'HK',  # Hong Kong
        '.L':  'GB',  # London
        '.TO': 'CA',  # Toronto
        '.AX': 'AU',  # Australia
        '.SS': 'CN',  # Shanghai
        '.SZ': 'CN',  # Shenzhen
    }
    for suffix, country in suffix_map.items():
        if ticker.endswith(suffix):
            return country

    # 숫자 티커
    if re.fullmatch(r'\d{6}', ticker):
        return 'KR'  # 한국x

    if re.fullmatch(r'\d{4}', ticker):
        return 'JP'  # 일본

    # 영문자 기반 판별
    if re.fullmatch(r'[A-Z]{1,4}', ticker):
        return 'US'  # 미국 (NYSE/NASDAQ)

    # 기타: 확실하지 않음
    return 'UNKNOWN'

# 연도별 개장일 정보를 메모리 캐시에 저장하여 반복적인 로딩을 방지합니다.
_TRADING_DAY_CACHE = {}

def get_trading_days(year: str, country_code: str = 'KR') -> list:
    # print(f"get_trading_days: {year}, {country_code}")
    """
    특정 연도의 모든 개장일을 데이터베이스 또는 yfinance에서 불러와 리스트로 반환합니다.
    각 나라별로 별도 관리
    
    Args:
        year (str): 연도 (예: '2024')
        country_code (str): 국가 코드 (예: 'KR', 'US', 'JP' etc.)
    
    Returns:
        list: 거래일 리스트
    """
    cache_key = f"{country_code}_{year}"
    if cache_key in _TRADING_DAY_CACHE:
        return _TRADING_DAY_CACHE[cache_key]

    # 먼저 데이터베이스에서 확인
    print(f"get_trading_days: {year}, {country_code} (데이터베이스에서 확인)")
    trading_days = load_trading_days_from_db(year, country_code)
    
    if trading_days:
        _TRADING_DAY_CACHE[cache_key] = trading_days
        print(f"get_trading_days: {year}, {country_code} 데이터베이스에서 로드됨")
        return trading_days

    # 대표 종목 가져오기
    representative_ticker = COUNTRY_REPRESENTATIVE_TICKERS.get(country_code, '005930.KS')

    # 데이터베이스에 없으면 API 호출
    try:
        # 각 나라별 대표 종목으로 거래일 조회
        ticker = yf.Ticker(representative_ticker)
        df = ticker.history(start=f"{year}-01-01", end=f"{int(year)+1}-01-01", interval="1d")
        if not df.empty:
            # timezone-aware datetime을 naive datetime으로 변환
            trading_days = [d.tz_localize(None) if d.tz is not None else d for d in df.index.to_list()]
            # 데이터베이스에 저장
            save_trading_days_to_db(trading_days, year, country_code)
            _TRADING_DAY_CACHE[cache_key] = trading_days
            print(f"get_trading_days: {year}, {country_code} 데이터가 저장되었습니다.")
            return trading_days

        else:
            print(f"[경고] yfinance에서 {country_code} {year} 데이터가 비어있습니다.")
            return []
    
    except Exception as e:
        print(f"[오류] yfinance에서 {country_code} {year} 데이터 조회 실패: {e}")
        return []

def split_dates_by_days(start_date: int, end_date: int, days=100) -> list:
    start = datetime.strptime(str(start_date), "%Y%m%d")
    end = datetime.strptime(str(end_date), "%Y%m%d")
    end = end + timedelta(days=1)

    date_list = []
    current_start = start

    while current_start < end:
        # 현재 시작 날짜의 연도 끝 (12월 31일)
        year_end = datetime(current_start.year, 12, 31)
        # 100일 뒤 날짜
        days_end = current_start + timedelta(days=days - 1)
        # 종료일은 세 조건 중 가장 빠른 것
        # current_end = min(year_end, days_end, end)
        current_end = min(days_end, end)

        print(f"current_start: {current_start}, end: {current_end}")

        start_str = int(current_start.strftime("%Y%m%d"))
        end_str = int(current_end.strftime("%Y%m%d"))
        date_list.append((start_str, end_str))

        # current_start = current_end + timedelta(days=1)
        current_start = current_end

    return date_list

def get_next_trading_day(base_date, country_code = "KR") -> str:
    """
        다음 거래일을 반환합니다.
    Args:
        base_date: 기준일 (str "YYYYMMDD" 형식 또는 int YYYYMMDD)
        country_code: 국가 코드 (예: 'KR', 'US', 'JP' 등)
    Returns:
        str: "YYYYMMDD" 형식의 다음 거래일
    """

    # 입력값을 문자열로 변환
    if isinstance(base_date, int):
        base_date_str = str(base_date)
    else:
        base_date_str = str(base_date)
    
    # 8자리 숫자인지 확인
    if len(base_date_str) != 8 or not base_date_str.isdigit():
        raise ValueError(f"날짜는 8자리 숫자여야 합니다. 입력값: {base_date}")
    
    base_date = datetime.strptime(base_date_str, "%Y%m%d")
    year = base_date.year

    while True:
        trading_days = get_trading_days(str(year), country_code=country_code)
        # timezone-naive datetime으로 변환하여 비교
        base_date_naive = base_date.replace(tzinfo=None) if base_date.tzinfo is not None else base_date
        future_days = [d for d in trading_days if (d.replace(tzinfo=None) if d.tzinfo is not None else d) >= base_date_naive]
        if future_days:
            return future_days[0].strftime("%Y%m%d")
    
        # 찾을 수 없을 때.
        # 올해 데이터를 뒤져본 것이라면 오늘 날짜를 return
        if year == datetime.now().year:
            return datetime.now().strftime("%Y%m%d")
        
        # 아니면 다음 연도로 넘어김.
        year += 1

def get_previous_trading_day(base_date, country_code = "KR") -> str:
    """
    이전 거래일을 반환합니다.
    Args:
        base_date: 기준일 (str "YYYYMMDD" 형식 또는 int YYYYMMDD)
        country_code: 국가 코드 (예: 'KR', 'US', 'JP' 등)
    Returns:
        str: "YYYYMMDD" 형식의 이전 거래일
    """
    # 입력값을 문자열로 변환
    if isinstance(base_date, int):
        base_date_str = str(base_date)
    else:
        base_date_str = str(base_date)
    
    # 8자리 숫자인지 확인
    if len(base_date_str) != 8 or not base_date_str.isdigit():
        raise ValueError(f"날짜는 8자리 숫자여야 합니다. 입력값: {base_date}")
    
    base_date = datetime.strptime(base_date_str, "%Y%m%d")
    year = base_date.year

    while True:
        trading_days = get_trading_days(str(year), country_code=country_code)
        # timezone-naive datetime으로 변환하여 비교
        base_date_naive = base_date.replace(tzinfo=None) if base_date.tzinfo is not None else base_date
        past_days = [d for d in trading_days if (d.replace(tzinfo=None) if d.tzinfo is not None else d) <= base_date_naive]
        if past_days:
            return past_days[-1].strftime("%Y%m%d")
        year -= 1

def get_trading_days_in_range(start_date_str: str, end_date_str: str, country_code = "KR") -> list:
    """
    시작일부터 종료일까지의 모든 개장일을 반환합니다.

    Args:
        start_date_str (str): "YYYYMMDD" 형식의 시작일
        end_date_str (str): "YYYYMMDD" 형식의 종료일

    Returns:
        list of datetime: 범위 내 개장일 리스트
    """
    start_date = datetime.strptime(start_date_str, "%Y%m%d")
    end_date = datetime.strptime(end_date_str, "%Y%m%d")

    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")

    print(f"get_trading_days_in_range: {start_date} ~ {end_date}")
    trading_days = []
    for year in range(start_date.year, end_date.year + 1):
        year_days = get_trading_days(str(year), country_code=country_code)
        trading_days.extend(year_days)

    # 범위 내로 필터링
    filtered_days = []
    for d in trading_days:
        # timezone-naive datetime으로 변환하여 비교
        d_naive = d.replace(tzinfo=None) if d.tzinfo is not None else d
        if start_date <= d_naive <= end_date:
            filtered_days.append(d_naive)
    return sorted(filtered_days)

def get_valid_date_range(start_date=None, end_date=None, day_padding=14):
    if start_date is None: # 시작일자 값이 없으면 day_padding 전 일자
        start_date = (datetime.now()-timedelta(days=day_padding)).strftime("%Y%m%d")   
    if  end_date is None:# 종료일자 값이 없으면 현재일자
        end_date  = datetime.today().strftime("%Y%m%d")   

    return start_date, end_date

def get_offset_date(base_date, offset_days):
    """
    기준 날짜에서 지정된 일수만큼 오프셋된 날짜를 반환합니다.
    Args:
        base_date (str or int): 기준 날짜 (YYYYMMDD 형식의 문자열 또는 정수)
        offset_days (int): 오프셋할 일수 (양수: 미래, 음수: 과거)
    Returns:
        str: YYYYMMDD 형식의 오프셋된 날짜
    """
    if isinstance(base_date, int):
        base_date = str(base_date)
    
    if len(base_date) != 8 or not base_date.isdigit():
        raise ValueError(f"날짜는 8자리 숫자여야 합니다. 입력값: {base_date}")
    
    base_date = datetime.strptime(base_date, "%Y%m%d")
    offset_date = base_date + timedelta(days=offset_days)
    
    return offset_date.strftime("%Y%m%d")

##############################################################################################
# 데이터 저장 관련 로직
##############################################################################################
def _check_date_exists_in_data(existing_data, target_date, date_column='date'):
    """기존 데이터에 특정 날짜가 있는지 확인"""
    if existing_data is None or existing_data.empty:
        return False
    
    # 날짜 컬럼이 있는지 확인하고 형변환
    if date_column in existing_data.columns:
        try:
            # 기존 데이터를 수정하지 않고 복사본에서 작업
            temp_data = existing_data.copy()
            temp_data[date_column] = pd.to_datetime(temp_data[date_column], format='%Y%m%d', errors='coerce')
            target_date_dt = pd.to_datetime(target_date, format='%Y%m%d')
            return target_date_dt in temp_data[date_column].values
        
        except Exception as e:
            print(f"날짜 확인 중 오류: {e}")
            return False
        
    print(f"날짜 컬럼 '{date_column}'이 데이터에 없습니다.")
    return False

##############################################################################################
# KIS API
##############################################################################################

##############################################################################################
# [국내주식] 기본시세 > 주식현재가 일자별  (최근 30일만 조회)
# 주식현재가 일자별 API입니다. 일/주/월별 주가를 확인할 수 있으며 최근 30일(주,별)로 제한되어 있습니다.
##############################################################################################
# 주식현재가 일자별 Object를 DataFrame 으로 반환
# Input: None (Option) 상세 Input값 변경이 필요한 경우 API문서 참조
# Output: DataFrame (Option) output
def get_daily_price(
        div_code="J", itm_no="", 
        period_code="D", adj_prc_code="0", tr_cont="", 
        dataframe=None
    ):  # [국내주식] 기본시세 > 주식현재가 일자별
    url = '/uapi/domestic-stock/v1/quotations/inquire-daily-price'
    tr_id = "FHKST01010400"  # 주식현재가 일자별

    params = {
        "FID_COND_MRKT_DIV_CODE": div_code, # 시장 분류 코드  J : 주식/ETF/ETN, W: ELW
        "FID_INPUT_ISCD": itm_no,           # 종목번호 (6자리) ETN의 경우, Q로 시작 (EX. Q500001)
        "FID_PERIOD_DIV_CODE": period_code, # 기간분류코드 D : (일)최근 30거래일, W : (주)최근 30주, M : (월)최근 30개월
        "FID_ORG_ADJ_PRC": adj_prc_code     # 0 : 수정주가반영, 1 : 수정주가미반영 * 수정주가는 액면분할/액면병합 등 권리 발생 시 과거 시세를 현재 주가에 맞게 보정한 가격
    }
    res = kis_fetcher.url_fetch(url, tr_id, tr_cont, params)

    # Assuming 'output' is a dictionary that you want to convert to a DataFrame
    current_data = pd.DataFrame(res.getBody().output)  # getBody() kis_auth.py 존재

    # Convert KIS column names to my_app format with dual header (Korean + my_app)
    dataframe = column_mapper.convert_dataframe_columns(current_data, as_is="kis", to_be="my_app")

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
    adj_prc="0",    # 수정주가 0:수정주가 1:원주가
    dataframe=None
) :
    country_code = get_country_code(itm_no)
    
    start_date, end_date = get_valid_date_range(start_date, end_date, day_padding=14)
    start_date = get_next_trading_day(start_date, country_code=country_code)
    end_date = get_previous_trading_day(end_date, country_code=country_code)

    print(f"조회 기간: {start_date} ~ {end_date}")

    url = '/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice'
    tr_id = "FHKST03010100"  # 주식현재가 회원사

    params = {
        "FID_COND_MRKT_DIV_CODE": div_code, # 시장 분류 코드  J : 주식/ETF/ETN, W: ELW
        "FID_INPUT_ISCD": itm_no,           # 종목번호 (6자리) ETN의 경우, Q로 시작 (EX. Q500001)
        "FID_INPUT_DATE_1": start_date,   # 입력 날짜 (시작) 조회 시작일자 (ex. 20220501)
        "FID_INPUT_DATE_2": end_date,    # 입력 날짜 (종료) 조회 종료일자 (ex. 20220530)
        "FID_PERIOD_DIV_CODE": period_code, # 기간분류코드 D:일봉, W:주봉, M:월봉, Y:년봉
        "FID_ORG_ADJ_PRC": adj_prc          # 수정주가 0:수정주가 1:원주가
    }
    
    print("API에서 새로운 데이터를 가져옵니다...")
    res = kis_fetcher.url_fetch(url, tr_id, tr_cont, params)

    # output1: 현재가 정보 (실시간 상태)
    current_data = pd.DataFrame(res.getBody().output1, index=[0])  # 현재가 정보

    # Convert KIS column name to my_app column 
    dataframe = column_mapper.convert_dataframe_columns(current_data, as_is="kis", to_be="my_app")
    
    # 새로운 데이터를 CSV에 저장 (기존 데이터와 병합)
    # result_data = _merge_and_save_data(existing_data, dataframe, csv_filepath)
    return dataframe

def get_itempricechart_2(
        div_code="J",   # 시장 분류 코드 J: 주식/ETF/ETN, W: ELW
        ticker="",      # 종목번호 (6자리) ETN의 경우, Q로 시작 (EX. Q500001)
        tr_cont="",     # 트랜잭션 내용 (선택사항)
        start_date=None, end_date=None, 
        period_code="D", adj_prc="0", dataframe=None
):  
    # 국내, 해외 종합 지수조회
    country_code = get_country_code(ticker)
    
    # 기존 데이터 로드
    existing_data = None

    start_date, end_date = get_valid_date_range(start_date, end_date, day_padding=14)
    _ori_start_date = start_date
    _ori_end_date = end_date

    date_list = split_dates_by_days(start_date, end_date, days=100)
    # print(date_list)

    result_data = None
    for st_date, ed_date in date_list:
        st_date = get_next_trading_day(st_date, country_code=country_code)
        ed_date = get_previous_trading_day(ed_date, country_code=country_code)

        print(f"조회 기간: {st_date} ~ {ed_date}")
        if(ed_date < st_date):
            st_date = ed_date

        existing_data = load_existing_data_from_db(ticker, st_date, ed_date, period_code, 'itemchartprice_history')

        blank_dates = []
        # 여전히 비어있으면
        if existing_data is not None and not existing_data.empty:
            # 기존 데이터에서 요청한 날짜 범위의 데이터가 모두 있는지 확인
            valid_date_list = get_trading_days_in_range(st_date, ed_date, country_code=country_code)
            for date in valid_date_list:
                date_str = date.strftime("%Y%m%d")
                if not check_date_exists_in_db(ticker, date_str, period_code, 'itemchartprice_history'):
                    blank_dates.append(date)
        else:
            blank_dates = get_trading_days_in_range(st_date, ed_date, country_code=country_code)

        # 빈 날짜가 있으면 빈 날짜에 대해 API 호출
        if blank_dates:
            sst_date = blank_dates[0]  # 첫 번째 빈 날짜로 시작일을 조정
            eed_date = blank_dates[-1]    # 마지막 빈 날짜로 종료일을 조정

            url = '/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice'
            tr_id = "FHKST03010100"  # 주식현재가 회원사
            if(country_code != 'KR'):
                url = "/uapi/overseas-price/v1/quotations/inquire-daily-chartprice"
                tr_id = "FHKST03030100"
                div_code = "N"

            params = {
                "FID_COND_MRKT_DIV_CODE": div_code, # 시장 분류 코드  J : 주식/ETF/ETN, W: ELW | N : 해외주식
                "FID_INPUT_ISCD": ticker,           # 종목번호 (6자리), 한국/미국 가능. 일본은 아직 몰루
                "FID_INPUT_DATE_1": sst_date.strftime("%Y%m%d"),   # 입력 날짜 (시작) 조회 시작일자 (ex. 20220501)
                "FID_INPUT_DATE_2": eed_date.strftime("%Y%m%d"),   # 입력 날짜 (종료) 조회 종료일자 (ex. 20220530)
                "FID_PERIOD_DIV_CODE": period_code, # 기간분류코드 D:일봉, W:주봉, M:월봉, Y:년봉
                "FID_ORG_ADJ_PRC": adj_prc          # 수정주가 0:수정주가 1:원주가
            }

            print("API에서 새로운 데이터를 가져옵니다...")
            res = kis_fetcher.url_fetch(url, tr_id, tr_cont, params)
            current_data = pd.DataFrame(res.getBody().output2)  # 기간별 일봉 데이터

            # Convert KIS column names to my_app format with dual header (Korean + my_app)
            col_as_is = "kis" if country_code == 'KR' else "kis_ovs"
            dataframe = column_mapper.convert_dataframe_columns(current_data, as_is=col_as_is, to_be="my_app")
            
            # 새로운 데이터를 데이터베이스에 저장
            save_data_to_db(dataframe, ticker, country_code, period_code, 'itemchartprice_history')
            
            # 결과 데이터에 병합
            if result_data is None:
                result_data = dataframe
            else:
                result_data = pd.concat([result_data, dataframe], ignore_index=True)
            
            print("API 요청 대기시간을 기다립니다...") 
            time.sleep(1)

        else:
            # 기존 데이터 사용
            print(f"기존 데이터에서 {st_date} ~ {ed_date} 기간의 데이터를 찾았습니다. API 호출을 건너뜁니다.")

            if result_data is None:
                result_data = existing_data
            else:
                result_data = pd.concat([result_data, existing_data], ignore_index=True)
    
    # 전체 기간 데이터 조회가 끝난 후, 한번에 필터링하여 반환
    try:
        if result_data is not None and not result_data.empty:
            result_data['date'] = pd.to_datetime(result_data['date'], format='%Y%m%d', errors='coerce')
            start_dt = pd.to_datetime(_ori_start_date, format='%Y%m%d')
            end_dt = pd.to_datetime(_ori_end_date, format='%Y%m%d')
            result_data = result_data[
                (result_data['date'] >= start_dt) & 
                (result_data['date'] <= end_dt)
            ].copy()
            
            # 날짜를 YYYYMMDD 형식으로 변환
            result_data['date'] = result_data['date'].dt.strftime('%Y%m%d')  # 날짜를 YYYYMMDD 형식으로 변환

            # 모든 열을 값을 보고 적절한 형으로 변환
            for col in result_data.columns:
                if col == 'date':
                    continue
                if result_data[col].dtype == 'object':
                    # 숫자형으로 변환 (오류가 나면 NaN 처리)
                    result_data[col] = pd.to_numeric(result_data[col], errors='coerce')
            
            # 날짜 기준으로 오름차순 정렬
            result_data = result_data.sort_values('date').reset_index(drop=True)
        else:
            result_data = pd.DataFrame()

    except Exception as e:
        print(f"데이터 필터링 중 오류: {e}")
        result_data = pd.DataFrame()

    return result_data

def get_full_ticker(include_screening_data=True):
    """
    pykrx를 사용해서 한국에 상장된 모든 ticker를 가져와서 데이터베이스에 저장
    스크리닝에 필요한 추가 데이터도 포함 가능
    
    Args:
        include_screening_data (bool): 스크리닝 데이터 포함 여부
    Returns:
        pd.DataFrame: ticker 정보가 담긴 DataFrame
    """
    
    # 오늘 날짜 기준으로 데이터베이스에서 최신 데이터가 있는지 확인
    try:
        existing_data = load_ticker_info_from_db()
        if not existing_data.empty and 'trading_date' in existing_data.columns:
            # 파일이 오늘 생성되었으면 기존 데이터 사용
            today = datetime.now().strftime("%Y%m%d")
            latest_trading_date = existing_data['trading_date'].iloc[0] if len(existing_data) > 0 else None
            
            if latest_trading_date == today:
                print(f"기존 ticker 데이터를 사용합니다 (데이터베이스)")
                return existing_data
    except Exception as e:
        print(f"기존 ticker 데이터 확인 중 오류: {e}")
    
    print("pykrx에서 최신 ticker 정보를 가져옵니다...")
    
    try:
        # 오늘 날짜 (거래일 기준으로 조정)
        today = datetime.now().strftime("%Y%m%d")
        # 최근 거래일로 조정 (주말이면 금요일 데이터 사용)
        try:
            trading_day = get_previous_trading_day(today)
        except:
            trading_day = today
        
        all_tickers = pd.DataFrame()
        
        # 시장별로 데이터 수집
        markets = ["KOSPI", "KOSDAQ"]
        
        for market_name in markets:
            print(f"{market_name} 종목 조회 중...")
            
            try:
                # 기본 ticker 리스트
                tickers = stock.get_market_ticker_list(date=trading_day, market=market_name)
                
                market_df = pd.DataFrame({
                    'ticker': tickers,
                    'market': market_name
                })
                
                # 종목명 추가
                names = []
                for ticker in tickers:
                    try:
                        name = stock.get_market_ticker_name(ticker)
                        names.append(name)
                    except:
                        names.append('Unknown')
                market_df['name'] = names
                
                # 스크리닝 데이터 추가
                if include_screening_data:
                    print(f"{market_name} 스크리닝 데이터 수집 중...")
                    
                    # 시가총액 및 기본 정보
                    try:
                        cap_df = stock.get_market_cap(date=trading_day, market=market_name)
                        if not cap_df.empty:
                            # ticker를 기준으로 병합
                            cap_df.reset_index(inplace=True)
                            cap_df.rename(columns={'티커': 'ticker'}, inplace=True)
                            
                            # 컬럼명 영어로 변경
                            cap_df.rename(columns={
                                '종목명': 'name_cap',
                                '시가총액': 'market_cap',
                                '주식수': 'shares',
                                '종가': 'close_price'
                            }, inplace=True)
                            
                            # market_df와 병합 (ticker 기준)
                            market_df = market_df.merge(
                                cap_df[['ticker', 'market_cap', 'shares', 'close_price']], 
                                on='ticker', 
                                how='left'
                            )
                    except Exception as e:
                        print(f"{market_name} 시가총액 데이터 조회 실패: {e}")
                    
                    # PER, PBR, DIV 등 추가
                    try:
                        fundamental_df = stock.get_market_fundamental(date=trading_day, market=market_name)
                        if not fundamental_df.empty:
                            fundamental_df.reset_index(inplace=True)
                            fundamental_df.rename(columns={'티커': 'ticker'}, inplace=True)
                            
                            # 컬럼명 영어로 변경
                            fundamental_df.rename(columns={
                                'BPS': 'bps',
                                'PER': 'per', 
                                'PBR': 'pbr',
                                'EPS': 'eps',
                                'DIV': 'dividend_yield',
                                'DPS': 'dps'
                            }, inplace=True)
                            
                            # market_df와 병합
                            fundamental_cols = ['ticker', 'bps', 'per', 'pbr', 'eps', 'dividend_yield', 'dps']
                            available_cols = ['ticker'] + [col for col in fundamental_cols[1:] if col in fundamental_df.columns]
                            
                            market_df = market_df.merge(
                                fundamental_df[available_cols], 
                                on='ticker', 
                                how='left'
                            )
                    except Exception as e:
                        print(f"{market_name} 펀더멘털 데이터 조회 실패: {e}")
                    
                    # 추가 데이터: 업종 정보
                    try:
                        # 개별 종목의 업종 정보 (시간이 오래 걸릴 수 있음)
                        sectors = []
                        print(f"{market_name} 업종 정보 수집 중... (시간이 걸릴 수 있습니다)")
                        
                        # 샘플링으로 처리 속도 향상 (전체가 너무 오래 걸리면)
                        for i, ticker in enumerate(tickers[:50]):  # 처음 50개만 샘플링
                            try:
                                # 종목의 업종 정보는 별도 API가 필요할 수 있음
                                sectors.append('Unknown')  # 일단 Unknown으로 처리
                            except:
                                sectors.append('Unknown')
                            
                            if i % 10 == 0:
                                print(f"  진행률: {i+1}/{min(50, len(tickers))}")
                        
                        # 나머지는 Unknown으로 채우기
                        sectors.extend(['Unknown'] * (len(tickers) - len(sectors)))
                        market_df['sector'] = sectors
                        
                    except Exception as e:
                        print(f"{market_name} 업종 정보 수집 실패: {e}")
                        market_df['sector'] = 'Unknown'
                
                all_tickers = pd.concat([all_tickers, market_df], ignore_index=True)
                print(f"{market_name}: {len(market_df)}개 종목 완료")
                
            except Exception as e:
                print(f"{market_name} 데이터 수집 실패: {e}")
                continue
        
        # KONEX 추가 (선택적)
        try:
            print("KONEX 종목 조회 중...")
            konex_tickers = stock.get_market_ticker_list(date=trading_day, market="KONEX")
            konex_df = pd.DataFrame({
                'ticker': konex_tickers,
                'market': 'KONEX'
            })
            
            # 종목명 추가
            konex_names = []
            for ticker in konex_tickers:
                try:
                    name = stock.get_market_ticker_name(ticker)
                    konex_names.append(name)
                except:
                    konex_names.append('Unknown')
            konex_df['name'] = konex_names
            
            # KONEX는 기본 정보만 (스크리닝 데이터는 제한적)
            if include_screening_data:
                for col in ['market_cap', 'shares', 'close_price', 'bps', 'per', 'pbr', 'eps', 'dividend_yield', 'dps', 'sector']:
                    if col not in konex_df.columns:
                        konex_df[col] = None
            
            all_tickers = pd.concat([all_tickers, konex_df], ignore_index=True)
            print(f"KONEX: {len(konex_df)}개 종목 완료")
            
        except Exception as e:
            print(f"KONEX 데이터 조회 실패 (무시하고 계속): {e}")
        
        # 업데이트 날짜 추가
        # all_tickers['updated_date'] = today
        all_tickers['trading_date'] = trading_day
        
        # 데이터 타입 정리
        if include_screening_data:
            # 숫자 컬럼들을 적절한 타입으로 변환
            numeric_cols = ['market_cap', 'shares', 'close_price', 'per', 'pbr', 'eps', 'bps', 'dividend_yield', 'dps']
            for col in numeric_cols:
                if col in all_tickers.columns:
                    all_tickers[col] = pd.to_numeric(all_tickers[col], errors='coerce')
        
        # 데이터베이스에 저장
        save_ticker_info_to_db(all_tickers)
        
        print(f"\n=== 수집 완료 ===")
        print(f"총 {len(all_tickers)}개의 ticker가 저장되었습니다.")
        
        market_counts = all_tickers['market'].value_counts()
        for market, count in market_counts.items():
            print(f"{market}: {count}개")
        
        if include_screening_data:
            print(f"\n스크리닝 데이터 컬럼: {[col for col in all_tickers.columns if col not in ['ticker', 'name', 'market', 'updated_date', 'trading_date']]}")
        
        print(f"데이터베이스에 저장 완료")
        
        return all_tickers
        
    except Exception as e:
        print(f"ticker 정보 조회 실패: {e}")
        
        # 실패시 기존 데이터가 있으면 반환
        existing_data = load_ticker_info_from_db()
        if not existing_data.empty:
            print("기존 ticker 데이터를 사용합니다.")
            return existing_data
        else:
            print("ticker 정보를 가져올 수 없습니다.")
            return pd.DataFrame()