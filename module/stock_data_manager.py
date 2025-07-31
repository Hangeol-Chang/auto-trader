'''
    TODO
    - 전체 데이터 검색에 대해, 로컬 db를 먼저 뒤져보고 없으면 가져와야 함. ✅ (CSV 캐싱 구현됨)
    - 그리고 가져온 데이터는 무조건 저장해둘 것. ✅ (CSV 저장 구현됨)
    
    ** COLUMN name 변환?
    - 변환은 여기서 전부 처리해야 함.
    - 이 파일 외부에서는 my_app의 column name만 사용할 것임.
    
    ** CSV 파일 저장 규칙:
    - {종목번호}_{API명}_{기간코드}.csv 형태로 저장
    - get_itempricechart_1: {종목번호}_itemchartprice_current_{기간코드}.csv
    - get_itempricechart_2: {종목번호}_itemchartprice_history_{기간코드}.csv
    - 데이터는 data/stock_cache/ 디렉토리에 저장됨
'''

import inspect
from unittest import result
import pandas as pd
import os
from datetime import datetime, timedelta
import yfinance as yf
import time
import re

# KIS API 관련 import 제거 (yfinance로 대체)
# import module.kis_fetcher as kis_fetcher
import module.column_mapper as column_mapper


DATA_DIR = "data"
# 날짜 관련
os.makedirs(DATA_DIR, exist_ok=True)

# 각 나라별 대표 종목 (거래일 조회용)
COUNTRY_REPRESENTATIVE_TICKERS = {
    'KR': '005930.KS',      # 삼성전자 (한국)
    'US': 'AAPL',           # Apple (미국)
    'JP': '7203.T',         # Toyota (일본)
    'CN': '000001.SS',      # 상해종합지수 ETF (중국)
    'HK': '0700.HK',        # Tencent (홍콩)
    'GB': 'LLOY.L',         # Lloyds Banking (영국)
    'CA': 'SHOP.TO',        # Shopify (캐나다)
    'AU': 'CBA.AX',         # Commonwealth Bank (호주)
}

##############################################################################################
# 날짜 관련 로직
##############################################################################################

# 티커에서 국가 코드 추출
def get_country_code_from_ticker(ticker: str) -> str:
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

def get_next_trading_day(base_date, ticker=None) -> str:
    """
        다음 거래일을 반환합니다.
    Args:
        base_date: 기준일 (str "YYYYMMDD" 형식 또는 int YYYYMMDD)
        ticker: 종목 코드 (국가 구분용, 없으면 한국 기본값)
        
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
    
    # 국가 코드 추출
    country_code = 'KR'  # 기본값
    if ticker:
        country_code = get_country_code_from_ticker(ticker)
    
    base_date = datetime.strptime(base_date_str, "%Y%m%d")
    year = base_date.year

    while True:
        trading_days = get_trading_days(str(year), country_code)
        future_days = [d for d in trading_days if d >= base_date]
        if future_days:
            return future_days[0].strftime("%Y%m%d")
    
        # 찾을 수 없을 때.
        # 올해 데이터를 뒤져본 것이라면 오늘 날짜를 return
        if year == datetime.now().year:
            return datetime.now().strftime("%Y%m%d")
        
        # 아니면 다음 연도로 넘어김.
        year += 1

def get_previous_trading_day(base_date, ticker=None) -> str:
    """
    이전 거래일을 반환합니다.
    
    Args:
        base_date: 기준일 (str "YYYYMMDD" 형식 또는 int YYYYMMDD)
        ticker: 종목 코드 (국가 구분용, 없으면 한국 기본값)
        
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
    
    # 국가 코드 추출
    country_code = 'KR'  # 기본값
    if ticker:
        country_code = get_country_code_from_ticker(ticker)
    
    base_date = datetime.strptime(base_date_str, "%Y%m%d")
    year = base_date.year

    while True:
        trading_days = get_trading_days(str(year), country_code)
        past_days = [d for d in trading_days if d <= base_date]
        if past_days:
            return past_days[-1].strftime("%Y%m%d")
        year -= 1

def get_trading_days_in_range(start_date_str: str, end_date_str: str, ticker=None) -> list:
    """
    시작일부터 종료일까지의 모든 개장일을 반환합니다.

    Args:
        start_date_str (str): "YYYYMMDD" 형식의 시작일
        end_date_str (str): "YYYYMMDD" 형식의 종료일
        ticker (str): 종목 코드 (국가 구분용, 없으면 한국 기본값)

    Returns:
        list of datetime: 범위 내 개장일 리스트
    """
    start_date = datetime.strptime(start_date_str, "%Y%m%d")
    end_date = datetime.strptime(end_date_str, "%Y%m%d")

    print(f"get_trading_days_in_range: {start_date} ~ {end_date}")
    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")

    # 국가 코드 추출
    country_code = 'KR'  # 기본값
    if ticker:
        country_code = get_country_code_from_ticker(ticker)

    trading_days = []
    print(f"get_trading_days_in_range: {start_date} ~ {end_date} ({country_code})")
    for year in range(start_date.year, end_date.year + 1):
        year_days = get_trading_days(str(year), country_code)
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

def _ensure_data_directory(country_code='KR'):
    """데이터 저장 디렉토리가 없으면 생성 (국가별)"""
    country_dir = os.path.join(DATA_DIR, country_code)
    if not os.path.exists(country_dir):
        os.makedirs(country_dir)
    return country_dir

def _generate_csv_filename(itm_no, api_name, period_code="D", country_code='KR'):
    """CSV 파일명 생성 규칙: {종목번호}_{API명}_{기간코드}.csv (국가별 디렉토리)"""
    return f"{itm_no}_{api_name}_{period_code}.csv"

def _get_csv_filepath(filename, country_code='KR'):
    """CSV 파일의 전체 경로 반환 (국가별)"""
    country_dir = _ensure_data_directory(country_code)
    return os.path.join(country_dir, filename)

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
        # 디렉토리가 없으면 생성
        os.makedirs(os.path.dirname(csv_filepath), exist_ok=True)
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
    # 두 데이터프레임 모두 날짜 컬럼을 문자열로 통일
    if existing_data is not None:
        existing_data[date_column] = existing_data[date_column].astype(str)
    
    print('existing_data:', existing_data.shape if existing_data is not None else 'None')
    print('new_data:', new_data.shape if new_data is not None else 'None')

    new_data[date_column] = new_data[date_column].astype(str)

    if existing_data is None or existing_data.empty:
        _save_data_to_csv(new_data, csv_filepath)
        return new_data

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
    ):  # [yfinance] 주식 일별 가격 데이터
    """
    yfinance를 사용하여 주식의 일별 가격 데이터를 가져옴
    
    Args:
        div_code (str): 시장 구분 (J: 주식, 사용되지 않음)
        itm_no (str): 종목번호 (6자리) 또는 티커
        period_code (str): 기간 코드 (D: 일, W: 주, M: 월)
        adj_prc_code (str): 수정주가 반영 여부 (0: 반영, 1: 미반영)
        tr_cont (str): 연속 조회 키 (사용되지 않음)
        dataframe: 기존 데이터프레임 (사용되지 않음)
    
    Returns:
        pd.DataFrame: 주식 가격 데이터
    """
    try:
        # 기간에 따른 period 설정
        if period_code == "D":
            period = "1mo"  # 최근 30일
        elif period_code == "W":
            period = "6mo"  # 최근 6개월 (주별 데이터)
        elif period_code == "M":
            period = "2y"   # 최근 2년 (월별 데이터)
        else:
            period = "1mo"  # 기본값
        
        # yfinance로 데이터 가져오기
        data = get_yfinance_data(itm_no, period=period)
        
        if data.empty:
            print(f"데이터를 가져올 수 없습니다: {itm_no}")
            return pd.DataFrame()
        
        # 기간에 따른 리샘플링
        if period_code == "W":
            # 주별 데이터로 리샘플링
            data = data.resample('W').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
        elif period_code == "M":
            # 월별 데이터로 리샘플링
            data = data.resample('M').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
        
        # 최근 30건으로 제한
        data = data.tail(30)
        
        # 날짜를 문자열 형태로 변환
        data = data.reset_index()
        data['date'] = data['date'].dt.strftime('%Y%m%d')
        
        return data
        
    except Exception as e:
        print(f"get_daily_price 오류: {e}")
        return pd.DataFrame()

##############################################################################################
# [국내주식] 기본시세 > 국내주식기간별시세(일/주/월/년)
# 국내주식기간별시세(일/주/월/년) API입니다.
# 실전계좌/모의계좌의 경우, 한 번의 호출에 최대 100건까지 확인 가능합니다.
##############################################################################################
# 국내주식기간별시세(일/주/월/년) Object를 DataFrame 으로 반환
# Input: None (Option) 상세 Input값 변경이 필요한 경우 API문서 참조
# Output: DataFrame (Option) output
def get_itempricechart_1(
    div_code="J",   # 시장 분류 코드 (사용되지 않음)
    itm_no="",      # 종목번호 (6자리) 또는 티커
    tr_cont="",     # 트랜잭션 내용 (사용되지 않음)
    start_date = None,
    end_date = None,
    period_code="D", 
    adj_prc="0",    # 수정주가 (yfinance는 기본적으로 수정주가 사용)
    dataframe=None
) :    
    """
    yfinance를 사용하여 주식의 현재가 정보를 가져옴
    
    Args:
        itm_no (str): 종목번호 또는 티커
        start_date, end_date: 사용되지 않음 (현재가 정보이므로)
        period_code (str): 기간 코드 (사용되지 않음)
        
    Returns:
        pd.DataFrame: 현재가 정보
    """
    try:
        # yfinance로 최신 데이터 가져오기 (1일치만)
        data = get_yfinance_data(itm_no, period='1d')
        
        if data.empty:
            print(f"현재가 데이터를 가져올 수 없습니다: {itm_no}")
            return pd.DataFrame()
        
        # 최신 데이터 1개만 선택
        latest_data = data.tail(1).copy()
        
        # 인덱스가 Date인 경우 컬럼으로 변환
        if 'date' not in latest_data.columns:
            latest_data = latest_data.reset_index()
        
        # 날짜를 문자열로 변환
        if 'date' in latest_data.columns:
            latest_data['date'] = pd.to_datetime(latest_data['date']).dt.strftime('%Y%m%d')
        elif 'Date' in latest_data.columns:
            latest_data['date'] = pd.to_datetime(latest_data['Date']).dt.strftime('%Y%m%d')
            latest_data = latest_data.drop('Date', axis=1)  # 기존 Date 컬럼 제거

        print(f"현재가 정보 조회 완료: {itm_no}")
        
        return latest_data
        
    except Exception as e:
        print(f"get_itempricechart_1 오류: {e}")
        return pd.DataFrame()

def get_itempricechart_2(
        div_code="J",   # 시장 분류 코드 (사용되지 않음)
        itm_no="",      # 종목번호 (6자리) 또는 티커
        tr_cont="",     # 트랜잭션 내용 (사용되지 않음)
        start_date=None, end_date=None, 
        period_code="D", adj_prc="0", dataframe=None
):  
    """
    yfinance를 사용하여 주식의 기간별 OHLCV 히스토리 데이터를 가져옴
    
    Args:
        itm_no (str): 종목번호 또는 티커
        start_date (str): 시작 날짜 (YYYYMMDD)
        end_date (str): 종료 날짜 (YYYYMMDD)
        period_code (str): 기간 코드 (D: 일봉, W: 주봉, M: 월봉)
        
    Returns:
        pd.DataFrame: 기간별 OHLCV 데이터
    """
    try:
        # 날짜 범위가 지정되지 않은 경우 기본값 설정
        if not start_date or not end_date:
            start_date, end_date = get_valid_date_range(start_date, end_date, day_padding=14)
        
        # yfinance로 데이터 가져오기
        data = get_yfinance_data(itm_no, start_date, end_date)
        
        if data.empty:
            print(f"히스토리 데이터를 가져올 수 없습니다: {itm_no}")
            return pd.DataFrame()
        
        # 기간에 따른 리샘플링
        if period_code == "W":
            # Date가 인덱스일 수 있으므로 확인 후 리샘플링
            if 'date' not in data.columns:
                # Date가 인덱스인 경우 그대로 리샘플링
                data = data.resample('W').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
                data = data.reset_index()  # 인덱스를 컬럼으로 변환
            else:
                # date가 컬럼인 경우 인덱스로 설정 후 리샘플링
                data = data.set_index('date').resample('W').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna().reset_index()
                
        elif period_code == "M":
            # Date가 인덱스일 수 있으므로 확인 후 리샘플링
            if 'date' not in data.columns:
                # Date가 인덱스인 경우 그대로 리샘플링
                data = data.resample('M').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
                data = data.reset_index()  # 인덱스를 컬럼으로 변환
            else:
                # date가 컬럼인 경우 인덱스로 설정 후 리샘플링
                data = data.set_index('date').resample('M').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna().reset_index()
        
        # 날짜를 문자열로 변환
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date']).dt.strftime('%Y%m%d')
        elif 'Date' in data.columns:
            data['date'] = pd.to_datetime(data['Date']).dt.strftime('%Y%m%d')
            data = data.drop('Date', axis=1)  # 기존 Date 컬럼 제거
        
        result_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        data = data[[col for col in result_columns if col in data.columns]]
        
        # 데이터 타입 변환
        for col in data.columns:
            if col != 'date':
                data[col] = pd.to_numeric(data[col], errors='coerce')
        
        print(f"히스토리 데이터 조회 완료: {itm_no} ({len(data)}건)")
        
        # 파일로 저장
        csv_filename = _generate_csv_filename(itm_no, "itemchartprice_history", period_code)
        csv_filepath = _get_csv_filepath(csv_filename, country_code=get_country_code_from_ticker(itm_no))

        data.to_csv(csv_filepath, index=False)
        print(f"히스토리 데이터 파일 저장 완료: {csv_filepath}")

        print(data)
        return data
        
    except Exception as e:
        print(f"get_itempricechart_2 오류: {e}")
        return pd.DataFrame()

def get_yfinance_data(
        ticker_code="",      # 종목번호 또는 티커
        start_date=None, 
        end_date=None, 
        period='1y'          # 기간 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
):
    """
    yfinance를 사용하여 주식 데이터를 가져오는 함수
    
    Args:
        ticker_code (str): 종목번호 또는 티커 (예: '005930', 'AAPL', '7203.T')
        start_date (str): 시작 날짜 (YYYY-MM-DD 또는 YYYYMMDD)
        end_date (str): 종료 날짜 (YYYY-MM-DD 또는 YYYYMMDD)
        period (str): 기간 ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
    
    Returns:
        pd.DataFrame: 주식 데이터 (Date, Open, High, Low, Close, Volume)
    """
    try:
        if not ticker_code:
            print("ticker_code가 제공되지 않았습니다.")
            return pd.DataFrame()
        
        # 한국 종목인 경우 yfinance 형식으로 변환
        yf_ticker = ticker_code
        if ticker_code.isdigit() and len(ticker_code) == 6:
            # 한국 종목 코드인 경우
            # KOSPI는 .KS, KOSDAQ은 .KQ 접미사 추가
            # 일단 .KS로 시도하고 실패하면 .KQ로 재시도
            yf_ticker = f"{ticker_code}.KS"
        
        # yfinance Ticker 객체 생성
        stock = yf.Ticker(yf_ticker)
        
        # 날짜 범위가 지정된 경우
        if start_date and end_date:
            # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
            if isinstance(start_date, str) and len(start_date) == 8:
                start_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
            if isinstance(end_date, str) and len(end_date) == 8:
                end_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
            
            data = stock.history(start=start_date, end=end_date)
        else:
            # 기간으로 데이터 가져오기
            data = stock.history(period=period)
        
        # 한국 종목에서 데이터가 없으면 KOSDAQ(.KQ)으로 재시도
        if data.empty and yf_ticker.endswith('.KS'):
            yf_ticker = yf_ticker.replace('.KS', '.KQ')
            stock = yf.Ticker(yf_ticker)
            
            if start_date and end_date:
                data = stock.history(start=start_date, end=end_date)
            else:
                data = stock.history(period=period)
        
        if data.empty:
            print(f"데이터를 찾을 수 없습니다: {ticker_code} ({yf_ticker})")
            return pd.DataFrame()
        
        # 인덱스를 컬럼으로 변환 (Date 인덱스를 date 컬럼으로)
        data = data.reset_index()        
        print(f"데이터 조회 완료: {ticker_code} ({yf_ticker}) - {len(data)}건")
        # 컬럼 매핑 (yfinance -> my_app)
        data = column_mapper.convert_dataframe_columns(data, 'yfi', 'my_app')
        return data
        
    except Exception as e:
        print(f"get_yfinance_data 오류: {e}")
        return pd.DataFrame()

def get_full_ticker(country_codes=['KR'], include_screening_data=True):
    """
    yfinance를 사용해서 다국가 주요 종목들의 ticker를 가져와서 CSV 파일로 저장
    
    Args:
        country_codes (list): 수집할 국가 코드 리스트 (예: ['KR', 'US', 'JP'])
        include_screening_data (bool): 스크리닝 데이터 포함 여부
    Returns:
        pd.DataFrame: ticker 정보가 담긴 DataFrame
    """
    country_suffix = "_".join(sorted(country_codes))
    if include_screening_data:
        ticker_file_path = os.path.join(DATA_DIR, f"{country_suffix}_ALL_TICKERS_WITH_SCREENING.csv")
    else:
        ticker_file_path = os.path.join(DATA_DIR, f"{country_suffix}_ALL_TICKERS.csv")
    
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
    
    print(f"yfinance에서 {country_codes} 주요 종목 정보를 가져옵니다...")
    
    try:
        # 다국가 주요 종목들 (yfinance에서 지원하는 종목들)
        major_tickers_by_country = {
            'KR': {
                # 한국 대형주
                '005930': {'name': '삼성전자', 'market': 'KOSPI'},
                '000660': {'name': 'SK하이닉스', 'market': 'KOSPI'},
                '035420': {'name': 'NAVER', 'market': 'KOSPI'},
                '005490': {'name': 'POSCO홀딩스', 'market': 'KOSPI'},
                '068270': {'name': '셀트리온', 'market': 'KOSPI'},
                '035720': {'name': '카카오', 'market': 'KOSPI'},
                '051910': {'name': 'LG화학', 'market': 'KOSPI'},
                '006400': {'name': '삼성SDI', 'market': 'KOSPI'},
                '028260': {'name': '삼성물산', 'market': 'KOSPI'},
                '012330': {'name': '현대모비스', 'market': 'KOSPI'},
                '066570': {'name': 'LG전자', 'market': 'KOSPI'},
                '003670': {'name': '포스코퓨처엠', 'market': 'KOSPI'},
                '096770': {'name': 'SK이노베이션', 'market': 'KOSPI'},
                '000270': {'name': '기아', 'market': 'KOSPI'},
                '005380': {'name': '현대차', 'market': 'KOSPI'},
                '207940': {'name': '삼성바이오로직스', 'market': 'KOSPI'},
                '373220': {'name': 'LG에너지솔루션', 'market': 'KOSPI'},
                # KOSDAQ 주요 종목
                '247540': {'name': '에코프로비엠', 'market': 'KOSDAQ'},
                '086520': {'name': '에코프로', 'market': 'KOSDAQ'},
                '058470': {'name': '리노공업', 'market': 'KOSDAQ'},
                '091990': {'name': '셀트리온헬스케어', 'market': 'KOSDAQ'},
                '196170': {'name': '알테오젠', 'market': 'KOSDAQ'},
                '039030': {'name': '이오테크닉스', 'market': 'KOSDAQ'},
                '277810': {'name': '레인보우로보틱스', 'market': 'KOSDAQ'},
            },
            'US': {
                # 미국 대형주
                'AAPL': {'name': 'Apple Inc.', 'market': 'NASDAQ'},
                'MSFT': {'name': 'Microsoft Corporation', 'market': 'NASDAQ'},
                'GOOGL': {'name': 'Alphabet Inc.', 'market': 'NASDAQ'},
                'AMZN': {'name': 'Amazon.com Inc.', 'market': 'NASDAQ'},
                'TSLA': {'name': 'Tesla Inc.', 'market': 'NASDAQ'},
                'META': {'name': 'Meta Platforms Inc.', 'market': 'NASDAQ'},
                'NVDA': {'name': 'NVIDIA Corporation', 'market': 'NASDAQ'},
                'JPM': {'name': 'JPMorgan Chase & Co.', 'market': 'NYSE'},
                'JNJ': {'name': 'Johnson & Johnson', 'market': 'NYSE'},
                'V': {'name': 'Visa Inc.', 'market': 'NYSE'},
                'PG': {'name': 'Procter & Gamble Co.', 'market': 'NYSE'},
                'UNH': {'name': 'UnitedHealth Group Inc.', 'market': 'NYSE'},
                'HD': {'name': 'Home Depot Inc.', 'market': 'NYSE'},
                'MA': {'name': 'Mastercard Inc.', 'market': 'NYSE'},
                'DIS': {'name': 'Walt Disney Co.', 'market': 'NYSE'},
            },
            'JP': {
                # 일본 대형주
                '7203.T': {'name': 'Toyota Motor Corp', 'market': 'TSE'},
                '6758.T': {'name': 'Sony Group Corp', 'market': 'TSE'},
                '9984.T': {'name': 'SoftBank Group Corp', 'market': 'TSE'},
                '6861.T': {'name': 'Keyence Corp', 'market': 'TSE'},
                '8306.T': {'name': 'Mitsubishi UFJ Financial Group', 'market': 'TSE'},
                '7974.T': {'name': 'Nintendo Co Ltd', 'market': 'TSE'},
                '4063.T': {'name': 'Shin-Etsu Chemical Co Ltd', 'market': 'TSE'},
                '6098.T': {'name': 'Recruit Holdings Co Ltd', 'market': 'TSE'},
            }
        }
        
        all_tickers = pd.DataFrame()
        
        for country_code in country_codes:
            if country_code not in major_tickers_by_country:
                print(f"국가 코드 {country_code}는 지원되지 않습니다.")
                continue
                
            major_tickers = major_tickers_by_country[country_code]
            print(f"\n=== {country_code} 종목 수집 중 ===")
            
            for ticker_code, info in major_tickers.items():
                try:
                    # yfinance 티커 형식 결정
                    if country_code == 'KR':
                        yf_ticker = f"{ticker_code}.KS" if info['market'] == 'KOSPI' else f"{ticker_code}.KQ"
                    else:
                        yf_ticker = ticker_code
                    
                    ticker_data = {
                        'ticker': ticker_code,
                        'yf_ticker': yf_ticker,
                        'name': info['name'],
                        'market': info['market'],
                        'country_code': country_code
                    }
                    
                    # 스크리닝 데이터 추가
                    if include_screening_data:
                        try:
                            print(f"{info['name']} ({ticker_code}) 데이터 수집 중...")
                            yf_stock = yf.Ticker(yf_ticker)
                            
                            # 기본 정보 가져오기
                            info_data = yf_stock.info
                            
                            if info_data:
                                ticker_data.update({
                                    'market_cap': info_data.get('marketCap'),
                                    'enterprise_value': info_data.get('enterpriseValue'),
                                    'pe_ratio': info_data.get('trailingPE'),
                                    'pb_ratio': info_data.get('priceToBook'),
                                    'dividend_yield': info_data.get('dividendYield'),
                                    'beta': info_data.get('beta'),
                                    'eps': info_data.get('trailingEps'),
                                    'book_value': info_data.get('bookValue'),
                                    'price_to_sales': info_data.get('priceToSalesTrailing12Months'),
                                    'sector': info_data.get('sector'),
                                    'industry': info_data.get('industry'),
                                    'website': info_data.get('website'),
                                    'business_summary': info_data.get('longBusinessSummary'),
                                    'full_time_employees': info_data.get('fullTimeEmployees'),
                                    'currency': info_data.get('currency'),
                                })
                                
                                # 최근 가격 정보
                                hist = yf_stock.history(period="5d")
                                if not hist.empty:
                                    ticker_data.update({
                                        'current_price': hist['Close'].iloc[-1],
                                        'volume': hist['Volume'].iloc[-1],
                                        'high_52w': info_data.get('fiftyTwoWeekHigh'),
                                        'low_52w': info_data.get('fiftyTwoWeekLow'),
                                    })
                            
                            time.sleep(0.3)  # API 호출 제한 고려
                            
                        except Exception as e:
                            print(f"{ticker_code} 스크리닝 데이터 수집 실패: {e}")
                            # 기본값으로 채우기
                            if include_screening_data:
                                for col in ['market_cap', 'enterprise_value', 'pe_ratio', 'pb_ratio', 
                                           'dividend_yield', 'beta', 'eps', 'book_value', 'price_to_sales',
                                           'sector', 'industry', 'website', 'business_summary', 
                                           'full_time_employees', 'current_price', 'volume', 'high_52w', 'low_52w', 'currency']:
                                    if col not in ticker_data:
                                        ticker_data[col] = None
                    
                    # DataFrame에 추가
                    ticker_df = pd.DataFrame([ticker_data])
                    all_tickers = pd.concat([all_tickers, ticker_df], ignore_index=True)
                    
                except Exception as e:
                    print(f"{ticker_code} 데이터 수집 실패: {e}")
                    continue
        
        # 업데이트 날짜 추가
        today = datetime.now().strftime("%Y%m%d")
        all_tickers['updated_date'] = today
        
        # 데이터 타입 정리
        if include_screening_data:
            # 숫자 컬럼들을 적절한 타입으로 변환
            numeric_cols = ['market_cap', 'enterprise_value', 'pe_ratio', 'pb_ratio', 
                           'dividend_yield', 'beta', 'eps', 'book_value', 'price_to_sales',
                           'current_price', 'volume', 'high_52w', 'low_52w', 'full_time_employees']
            for col in numeric_cols:
                if col in all_tickers.columns:
                    all_tickers[col] = pd.to_numeric(all_tickers[col], errors='coerce')
        
        # CSV 파일로 저장
        os.makedirs(DATA_DIR, exist_ok=True)
        all_tickers.to_csv(ticker_file_path, index=False, encoding='utf-8-sig')
        
        print(f"\n=== 수집 완료 ===")
        print(f"총 {len(all_tickers)}개의 ticker가 저장되었습니다.")
        
        country_counts = all_tickers['country_code'].value_counts()
        for country, count in country_counts.items():
            print(f"{country}: {count}개")
        
        if include_screening_data:
            print(f"\n스크리닝 데이터 컬럼: {[col for col in all_tickers.columns if col not in ['ticker', 'yf_ticker', 'name', 'market', 'country_code', 'updated_date']]}")
        
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
# 처리된 데이터 저장 디렉토리 생성
##############################################################################################
def extract_country_code_from_ticker(ticker):
    """
    티커에서 국가 코드를 추출
    
    Args:
        ticker (str): 주식 티커 (예: '005930', 'AAPL', '7203.T', '0700.HK')
    
    Returns:
        str: 국가 코드 (예: 'KR', 'US', 'JP', 'HK')
    """
    if '.' in ticker:
        suffix = ticker.split('.')[-1].upper()
        suffix_to_country = {
            'KS': 'KR',      # 한국 KOSPI
            'KQ': 'KR',      # 한국 KOSDAQ
            'T': 'JP',       # 일본 도쿄증권거래소
            'HK': 'HK',      # 홍콩
            'SS': 'CN',      # 중국 상하이
            'SZ': 'CN',      # 중국 선전
            'L': 'GB',       # 영국 런던
            'TO': 'CA',      # 캐나다 토론토
            'AX': 'AU',      # 호주
            'F': 'DE',       # 독일 프랑크푸르트
            'PA': 'FR',      # 프랑스 파리
        }
        return suffix_to_country.get(suffix, 'US')  # 기본값 미국
    else:
        # 한국 코드 (6자리 숫자)인지 확인
        if ticker.isdigit() and len(ticker) == 6:
            return 'KR'
        else:
            return 'US'  # 기본값 미국