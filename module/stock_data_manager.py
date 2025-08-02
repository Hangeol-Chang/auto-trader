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


DATA_DIR = "data"
# 날짜 관련
os.makedirs(DATA_DIR, exist_ok=True)

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
        return 'KR'  # 한국

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
    특정 연도의 모든 개장일을 CSV 파일 또는 yfinance에서 불러와 리스트로 반환합니다.
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

    # 국가별 디렉토리 생성
    country_dir = os.path.join(DATA_DIR, "date", country_code)
    print(f"get_trading_days: {year}, {country_code} {country_dir}")
    os.makedirs(country_dir, exist_ok=True)
    file_path = os.path.join(country_dir, f"TRADING_DATE_{year}.csv")

    # 대표 종목 가져오기
    representative_ticker = COUNTRY_REPRESENTATIVE_TICKERS.get(country_code, '005930.KS')

    # 날짜가 올해면 API 호출
    try:
        # 각 나라별 대표 종목으로 거래일 조회
        ticker = yf.Ticker(representative_ticker)
        df = ticker.history(start=f"{year}-01-01", end=f"{int(year)+1}-01-01", interval="1d")
        if not df.empty:
            trading_days = df.index.to_list()
            # CSV 파일로 저장
            df_to_save = pd.DataFrame({'date': [d.strftime("%Y%m%d") for d in trading_days]})
            df_to_save.to_csv(file_path, index=False)
            _TRADING_DAY_CACHE[cache_key] = trading_days
            print(f"get_trading_days: {year}, {country_code} 데이터가 저장되었습니다.")

        else:
            print(f"[경고] yfinance에서 {country_code} {year} 데이터가 비어있습니다.")
            return []
    
    except Exception as e:
        print(f"[오류] yfinance에서 {country_code} {year} 데이터 조회 실패: {e}")
        return []

    if os.path.exists(file_path):
        # CSV 파일에서 개장일 불러오기
        print(f"get_trading_days: {year}, {country_code} {file_path} exists")
        try:
            df = pd.read_csv(file_path)
            trading_days = [datetime.strptime(str(d), "%Y%m%d") for d in df['date']]
            _TRADING_DAY_CACHE[cache_key] = trading_days
            return trading_days
        except Exception as e:
            print(f"[오류] {file_path} 읽기 실패: {e}")
            return []

def split_dates_by_days(start_date: int, end_date: int, days=100) -> list:
    start = datetime.strptime(str(start_date), "%Y%m%d")
    end = datetime.strptime(str(end_date), "%Y%m%d")

    date_list = []
    current_start = start

    while current_start <= end:
        # 현재 시작 날짜의 연도 끝 (12월 31일)
        year_end = datetime(current_start.year, 12, 31)
        # 100일 뒤 날짜
        days_end = current_start + timedelta(days=days - 1)
        # 종료일은 세 조건 중 가장 빠른 것
        current_end = min(year_end, days_end, end)

        start_str = int(current_start.strftime("%Y%m%d"))
        end_str = int(current_end.strftime("%Y%m%d"))
        date_list.append((start_str, end_str))

        current_start = current_end + timedelta(days=1)

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
        future_days = [d for d in trading_days if d >= base_date]
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
        past_days = [d for d in trading_days if d <= base_date]
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
    filtered_days = [d for d in trading_days if start_date <= d <= end_date]
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

def _ensure_data_directory():
    """데이터 저장 디렉토리가 없으면 생성"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def _generate_csv_filename(itm_no, api_name, period_code="D"):
    """CSV 파일명 생성 규칙: {종목번호}_{API명}_{기간코드}.csv"""
    return f"{itm_no}_{api_name}_{period_code}.csv"

def _get_csv_filepath(filename, country_code='KR'):
    """CSV 파일의 전체 경로 반환"""
    return os.path.join(DATA_DIR, country_code, filename)

def _load_existing_data(csv_filepath):
    """기존 CSV 파일에서 데이터 로드"""
    if os.path.exists(csv_filepath):
        try:
            # 날짜 컬럼을 문자열로 읽어오도록 dtype 지정
            return pd.read_csv(csv_filepath, dtype={'date': str})
        except Exception as e:
            print(f"CSV 파일 로드 실패: {e}")
            return None
    return None

def _save_data_to_csv(dataframe, csv_filepath):
    """데이터를 CSV 파일로 저장"""
    try:
        _ensure_data_directory()
        # 날짜순으로 정렬하여 저장
        dataframe_sorted = dataframe.sort_values(by='date').reset_index(drop=True)
        dataframe_sorted.to_csv(csv_filepath, index=False, encoding='utf-8-sig')
        print(f"데이터가 저장되었습니다: {csv_filepath}")
    except Exception as e:
        print(f"CSV 파일 저장 실패: {e}")

def _merge_and_save_data(existing_data, new_data, csv_filepath, date_column='date'):
    """
    기존 데이터와 새 데이터를 병합하여 저장 (개선된 버전)
    - 날짜를 문자열로 다루어 안정성 확보
    """
    # date가 datetime으로 되어있으면 YYYYMMDD로 변환
    if date_column in new_data.columns:
        if pd.api.types.is_datetime64_any_dtype(new_data[date_column]):
            new_data[date_column] = new_data[date_column].dt.strftime('%Y%m%d')

    if existing_data is None or existing_data.empty:
        _save_data_to_csv(new_data, csv_filepath)
        return new_data

    if date_column in existing_data.columns:
        if pd.api.types.is_datetime64_any_dtype(existing_data[date_column]):
            existing_data[date_column] = existing_data[date_column].dt.strftime('%Y%m%d')
    try:
        combined_data = pd.concat([existing_data, new_data], ignore_index=True)
        # 날짜 기준으로 중복 제거 (API로 새로 받은 데이터를 우선)
        combined_data = combined_data.drop_duplicates(subset=[date_column], keep='last')
        _save_data_to_csv(combined_data, csv_filepath)
        return combined_data
    except Exception as e:
        print(f"데이터 병합 실패: {e}")
        # 병합 실패 시 새 데이터만 반환 (기존 데이터 손실 방지)
        return new_data

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
    res = kis_fetcher._url_fetch(url, tr_id, tr_cont, params)

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
    res = kis_fetcher._url_fetch(url, tr_id, tr_cont, params)

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
    
    # CSV 파일명 생성 (API 이름에 output2를 추가해 구분)
    csv_filename = _generate_csv_filename(ticker, "itemchartprice_history", period_code)
    csv_filepath = _get_csv_filepath(csv_filename, country_code=country_code)
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

        existing_data = _load_existing_data(csv_filepath)

        blank_dates = []
        # 여전히 비어있으면
        if existing_data is not None and not existing_data.empty:
            # 기존 데이터에서 요청한 날짜 범위의 데이터가 모두 있는지 확인
            valid_date_list = get_trading_days_in_range(st_date, ed_date, country_code=country_code)
            for date in valid_date_list:
                if not _check_date_exists_in_data(existing_data, date):
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
            res = kis_fetcher._url_fetch(url, tr_id, tr_cont, params)

            current_data = pd.DataFrame(res.getBody().output2)  # 기간별 일봉 데이터
            # Convert KIS column names to my_app format with dual header (Korean + my_app)
            col_as_is = "kis" if country_code == 'KR' else "kis_ovs"
            dataframe = column_mapper.convert_dataframe_columns(current_data, as_is=col_as_is, to_be="my_app")
            # 새로운 데이터를 CSV에 저장 (기존 데이터와 병합))
            result_data = _merge_and_save_data(existing_data, dataframe, csv_filepath)
            print("API 요청 대기시간을 기다립니다...") 
            time.sleep(1)

        else:
            # date 병합
            print(f"기존 데이터에서 {st_date} ~ {ed_date} 기간의 데이터를 찾았습니다. API 호출을 건너뜁니다.")

            filtered_data = existing_data[
                (existing_data['date'] >= st_date) & 
                (existing_data['date'] <= ed_date)
            ].copy()
            result_data = pd.concat([result_data, filtered_data], ignore_index=True)
    # 전체 기간 데이터 조회가 끝난 후, 한번에 필터링하여 반환
    try:
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

    except Exception as e:
        print(f"데이터 필터링 중 오류: {e}")

    return result_data

def get_full_ticker(include_screening_data=True):
    """
    pykrx를 사용해서 한국에 상장된 모든 ticker를 가져와서 CSV 파일로 저장
    스크리닝에 필요한 추가 데이터도 포함 가능
    
    Args:
        include_screening_data (bool): 스크리닝 데이터 포함 여부
    Returns:
        pd.DataFrame: ticker 정보가 담긴 DataFrame
    """
    if include_screening_data:
        ticker_file_path = os.path.join(DATA_DIR, "KR_ALL_TICKERS_WITH_SCREENING.csv")
    else:
        ticker_file_path = os.path.join(DATA_DIR, "KR_ALL_TICKERS.csv")
    
    # 오늘 날짜 기준으로 파일이 있고 최신이면 기존 파일 사용
    if os.path.exists(ticker_file_path):
        try:
            # 파일 수정 시간 확인
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(ticker_file_path))
            today = datetime.now().date()
            
            # 파일이 오늘 생성되었으면 기존 파일 사용
            if file_mod_time.date() == today:
                print(f"기존 ticker 파일을 사용합니다: {ticker_file_path}")
                return pd.read_csv(ticker_file_path)
        except Exception as e:
            print(f"기존 ticker 파일 확인 중 오류: {e}")
    
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
        
        # CSV 파일로 저장
        _ensure_data_directory()
        all_tickers.to_csv(ticker_file_path, index=False, encoding='utf-8-sig')
        
        print(f"\n=== 수집 완료 ===")
        print(f"총 {len(all_tickers)}개의 ticker가 저장되었습니다.")
        
        market_counts = all_tickers['market'].value_counts()
        for market, count in market_counts.items():
            print(f"{market}: {count}개")
        
        if include_screening_data:
            print(f"\n스크리닝 데이터 컬럼: {[col for col in all_tickers.columns if col not in ['ticker', 'name', 'market', 'updated_date', 'trading_date']]}")
        
        print(f"파일 저장 위치: {ticker_file_path}")
        
        return all_tickers
        
    except Exception as e:
        print(f"ticker 정보 조회 실패: {e}")
        
        # 실패시 기존 파일이 있으면 반환
        if os.path.exists(ticker_file_path):
            print("기존 ticker 파일을 사용합니다.")
            return pd.read_csv(ticker_file_path)
        else:
            print("ticker 정보를 가져올 수 없습니다.")
            return pd.DataFrame()


##############################################################################################
# data processing api
##############################################################################################
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")


##############################################################################################
# 처리된 데이터 저장 디렉토리 생성
##############################################################################################
def _ensure_processed_data_directory():
    """처리된 데이터 저장 디렉토리가 없으면 생성"""
    if not os.path.exists(PROCESSED_DATA_DIR):
        os.makedirs(PROCESSED_DATA_DIR)

###############################################################################################
# daily data를 이용해서 계산할 지표 전부 처리
###############################################################################################
def get_processed_data_D(
        itm_no="",      # 종목번호 (6자리) ETN의 경우, Q로 시작 (EX. Q500001)
        start_date=None, end_date=None,
        short_window=12, long_window=26, signal_window=9,
        center_window=20
    ):
    period_code = "D"  # 기간코드 (일봉) 
    """
    주식 데이터를 가져와서 MACD 지표와 rolling center를 계산하여 저장
    
    Args:
        itm_no (str): 종목번호 (6자리)
        start_date (str): 시작날짜 YYYYMMDD
        end_date (str): 종료날짜 YYYYMMDD  
        short_window (int): MACD 단기 이동평균 기간 (기본: 12)
        long_window (int): MACD 장기 이동평균 기간 (기본: 26)
        signal_window (int): MACD 신호선 기간 (기본: 9)
        center_window (int): rolling center 기간 (기본: 20)
    
    Returns:
        pd.DataFrame: 처리된 데이터프레임
    """
    start_date, end_date = get_valid_date_range(start_date, end_date, day_padding = 14)
    
    # 처리된 데이터 파일명 생성 규칙: {종목번호}_macd_{기간코드}.csv
    processed_filename = f"{itm_no}_processed_{period_code}.csv"
    processed_filepath = os.path.join(PROCESSED_DATA_DIR, processed_filename)
    
    # 캐시된 처리 데이터가 있는지 확인
    if os.path.exists(processed_filepath):
        try:
            existing_processed = pd.read_csv(processed_filepath)
            # 요청한 날짜 범위가 이미 처리되어 있는지 확인
                
            if not existing_processed.empty and 'date' in existing_processed.columns:
                existing_processed['date'] = pd.to_datetime(existing_processed['date'], format='%Y%m%d', errors='coerce')
                
                if start_date and end_date:
                    start_dt = pd.to_datetime(start_date, format='%Y%m%d')
                    end_dt = pd.to_datetime(end_date, format='%Y%m%d')
                    
                    # 요청한 범위의 데이터가 모두 있는지 확인 -> TODO : 이부분 로직 바꿔야함.
                    filtered_existing = existing_processed[
                        (existing_processed['date'] >= start_dt) & 
                        (existing_processed['date'] <= end_dt)
                    ]
                    print(f"요청한 날짜 범위: {start_dt} ~ {end_dt}")
                    print(f"캐시된 데이터에서 필터링된 행 수: {(filtered_existing)}")
                    
                    if len(filtered_existing) > 0:
                        print(f"캐시된 데이터를 사용합니다: {processed_filename}")
                        # 날짜를 다시 문자열로 변환
                        filtered_existing['date'] = filtered_existing['date'].dt.strftime('%Y%m%d')
                        return filtered_existing
        except Exception as e:
            print(f"기존 데이터 확인 중 오류: {e}")

    # processed_filepath가 존재하지 않거나 유효한 데이터가 없으면 새로 만들기
    try:
        # get_itempricechart_2에서 원시 데이터 가져오기
        print(f"getting raw stock data '{itm_no}' | '{period_code}' ...")
        raw_data = get_itempricechart_2(
            itm_no=itm_no,
            start_date=start_date,
            end_date=end_date,
            period_code=period_code
        )
        
        if raw_data is None or raw_data.empty:
            print("원시 데이터를 가져올 수 없습니다.")
            return pd.DataFrame()
        
        # date, close 컬럼만 유지
        if 'date' not in raw_data.columns or 'close' not in raw_data.columns:
            print(f"필수 컬럼이 없습니다. 사용 가능한 컬럼: {raw_data.columns.tolist()}")
            return pd.DataFrame()
        
        # 필요한 컬럼만 선택하고 복사본 생성
        processed_data = raw_data[['date', 'close']].copy()

        # 날짜 기준으로 정렬
        processed_data['date'] = pd.to_datetime(processed_data['date'], format='%Y%m%d', errors='coerce')
        processed_data = processed_data.sort_values('date').reset_index(drop=True)

        # close를 숫자로 변환
        processed_data['close'] = pd.to_numeric(processed_data['close'], errors='coerce')
        # 결측값 제거
        processed_data = processed_data.dropna()
        
        if len(processed_data) < max(long_window, center_window):
            print(f"데이터가 부족합니다. 최소 {max(long_window, center_window)}일 이상의 데이터가 필요합니다.")
            return pd.DataFrame()
                
        print("PROCESSING ...")

        print("- Rolling center 계산 중...")
        processed_data['center'] = processed_data['close'].rolling(window=center_window).mean()
        processed_data['upper_band'] = processed_data['center'] + 2 * processed_data['close'].rolling(window=center_window).std()
        processed_data['lower_band'] = processed_data['center'] - 2 * processed_data['close'].rolling(window=center_window).std()

        # MACD 계산
        # EMA 계산
        exp1 = processed_data['close'].ewm(span=short_window).mean()  # 12일 EMA
        exp2 = processed_data['close'].ewm(span=long_window).mean()   # 26일 EMA
        
        # MACD Line
        processed_data['macd'] = exp1 - exp2
        
        # Signal Line (MACD의 9일 EMA)
        processed_data['macd_signal'] = processed_data['macd'].ewm(span=signal_window).mean()
        
        # MACD Histogram
        processed_data['macd_histogram'] = processed_data['macd'] - processed_data['macd_signal']

        # 추가적인 기술적 지표들
        processed_data['sma_short'] = processed_data['close'].rolling(window=short_window).mean()
        processed_data['sma_long'] = processed_data['close'].rolling(window=long_window).mean()

        # 날짜를 다시 문자열로 변환 (저장을 위해)
        processed_data['date'] = processed_data['date'].dt.strftime('%Y%m%d')

        # 처리된 데이터 저장
        _ensure_processed_data_directory()
        processed_data.to_csv(processed_filepath, index=False, encoding='utf-8-sig')
        
        print(f"MACD 데이터 처리 완료: {processed_filename}")
        print(f"처리된 데이터 행 수: {len(processed_data)}")
        print(f"컬럼: {processed_data.columns.tolist()}")
        print(f"저장 위치: {processed_filepath}")
        
        # 요청한 날짜 범위로 필터링
        if start_date and end_date:
            processed_data['date_dt'] = pd.to_datetime(processed_data['date'], format='%Y%m%d')
            start_dt = pd.to_datetime(start_date, format='%Y%m%d')
            end_dt = pd.to_datetime(end_date, format='%Y%m%d')
            
            filtered_data = processed_data[
                (processed_data['date_dt'] >= start_dt) & 
                (processed_data['date_dt'] <= end_dt)
            ].drop('date_dt', axis=1).copy()
            
            return filtered_data
        
        return processed_data
        
    except Exception as e:
        print(f"MACD 데이터 처리 실패: {e}")
        return pd.DataFrame()
    
def get_processed_data_M(
        itm_no="",      # 종목번호 (6자리) ETN의 경우, Q로 시작 (EX. Q500001)
        start_date=None, end_date=None,
    ):
    period_code = "M"  # 기간코드 (월봉)

    """
    월봉 데이터를 가져와서 처리된 데이터를 반환합니다.
    Args:
        itm_no (str): 종목번호 (6자리)
        start_date (str): 시작날짜 YYYYMMDD
        end_date (str): 종료날짜 YYYYMMDD
    """

    start_date, end_date = get_valid_date_range(start_date, end_date, day_padding=14)
    # start_date를 1년 전으로 땡김
    start_date = get_offset_date(start_date, -365)

    processed_filename = f"{itm_no}_processed_{period_code}.csv"
    processed_filepath = os.path.join(PROCESSED_DATA_DIR, processed_filename)

    if os.path.exists(processed_filepath):
        try:
            existing_processed = pd.read_csv(processed_filepath)
            if not existing_processed.empty and 'date' in existing_processed.columns:
                existing_processed['date'] = pd.to_datetime(existing_processed['date'], format='%Y%m%d', errors='coerce')
                
                if start_date and end_date:
                    start_dt = pd.to_datetime(start_date, format='%Y%m%d')
                    end_dt = pd.to_datetime(end_date, format='%Y%m%d')
                    
                    # 요청한 범위의 데이터가 모두 있는지 확인 -> TODO : 이부분 로직 바꿔야함.
                    filtered_existing = existing_processed[
                        (existing_processed['date'] >= start_dt) & 
                        (existing_processed['date'] <= end_dt)
                    ]
                    
                    if len(filtered_existing) > 0:
                        print(f"캐시된 월봉 데이터를 사용합니다: {processed_filename}")
                        filtered_existing['date'] = filtered_existing['date'].dt.strftime('%Y%m%d')
                        return filtered_existing
        except Exception as e:
            print(f"기존 월봉 데이터 확인 중 오류: {e}")

    try:
        print(f"getting raw stock data '{itm_no}' | '{period_code}' ...")

        raw_data = get_itempricechart_2(
            itm_no=itm_no,
            start_date=start_date,
            end_date=end_date,
            period_code=period_code
        )
        
        if raw_data is None or raw_data.empty:
            print("원시 월봉 데이터를 가져올 수 없습니다.")
            return pd.DataFrame()

        # date, close 컬럼만 유지
        if 'date' not in raw_data.columns or 'close' not in raw_data.columns:
            print(f"필수 컬럼이 없습니다. 사용 가능한 컬럼: {raw_data.columns.tolist()}")
            return pd.DataFrame()

        # 필요한 컬럼만 선택하고 복사본 생성
        processed_data = raw_data[['date', 'close']].copy()

        # 날짜 기준으로 정렬
        processed_data['date'] = pd.to_datetime(processed_data['date'], format='%Y%m%d', errors='coerce')
        processed_data = processed_data.sort_values('date').reset_index(drop=True)

        # close를 숫자로 변환
        processed_data['close'] = pd.to_numeric(processed_data['close'], errors='coerce')
        # 결측값 제거
        processed_data = processed_data.dropna()

        print("PROCESSING ...")

        processed_data['BF_1M_close'] = processed_data['close'].shift(1)  # 이전 월봉 종가
        processed_data['BF_12M_close'] = processed_data['close'].shift(12)  # 12개월 전 종가
        
        # processed_data['trade'] = 

        print(processed_data)
        return processed_data

    except Exception as e:
        print(f"월봉 원시 데이터 가져오기 실패: {e}")
        return pd.DataFrame()