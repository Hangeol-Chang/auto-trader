'''
    암호화폐 데이터 관리 모듈 (Upbit API 기반)
    
    RULES
    - column name은 무조건 소문자로 작성.
    - 이 파일 외부에서 column_name을 my_app의 것으로만 사용
    - 이 파일 외부에서 날짜는 YYYYMMDD 형식, 시간은 YYYYMMDDHHMM 형식으로 사용
    - 암호화폐는 24시간 거래되므로 거래일 체크 로직 불필요
    
    TODO
    ** COLUMN name 변환?
    - 변환은 여기서 전부 처리해야 함.
    - 이 파일 외부에서는 my_app의 column name만 사용할 것임.
    
    ** CSV 파일 저장 규칙:
    - {심볼}_{API명}_{기간코드}.csv 형태로 저장
    - get_candle_data: {심볼}_candle_{기간코드}.csv
    - 데이터는 data/crypto_cache/ 디렉토리에 저장됨
'''

import pandas as pd
import os
import requests
import time
import sqlite3
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    import module.column_mapper as column_mapper
except ImportError:
    # 상대 import 시도
    column_mapper = None

# 캐시 디렉토리 설정
CRYPTO_CACHE_DIR = "data/crypto_cache"
DATA_DIR = "data"
CRYPTO_DB_PATH = os.path.join(DATA_DIR, "crypto_data.db")

if not os.path.exists(CRYPTO_CACHE_DIR):
    os.makedirs(CRYPTO_CACHE_DIR)
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Upbit API 엔드포인트
UPBIT_BASE_URL = "https://api.upbit.com/v1"

##############################################################################################
# 유틸리티 함수들
##############################################################################################

def format_datetime_to_iso(dt_str: str) -> str:
    """
    YYYYMMDDHHMM 형식을 ISO 8601 형식으로 변환
    Args:
        dt_str: YYYYMMDDHHMM 형식의 문자열
    Returns:
        ISO 8601 형식의 문자열 (UTC)
    """
    if len(dt_str) == 8:  # YYYYMMDD
        dt_str += "0000"  # 00시 00분으로 보정
    
    if len(dt_str) != 12:
        raise ValueError(f"날짜 시간은 YYYYMMDDHHMM 형식이어야 합니다. 입력값: {dt_str}")
    
    dt = datetime.strptime(dt_str, "%Y%m%d%H%M")
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

def format_iso_to_datetime(iso_str: str) -> str:
    """
    ISO 8601 형식을 YYYYMMDDHHMM 형식으로 변환
    Args:
        iso_str: ISO 8601 형식의 문자열
    Returns:
        YYYYMMDDHHMM 형식의 문자열
    """
    # Z나 +00:00 같은 타임존 정보 제거
    iso_str = iso_str.replace('Z', '').split('+')[0].split('T')
    date_part = iso_str[0].replace('-', '')
    if len(iso_str) > 1:
        time_part = iso_str[1].replace(':', '')[:4]  # HHMM만 추출
        return date_part + time_part
    else:
        return date_part + "0000"

##############################################################################################
# Upbit API 캔들 데이터 조회 함수들
##############################################################################################

def get_upbit_candle_data(market: str, interval: str, count: int = 200, to: str = None) -> Optional[pd.DataFrame]:
    """
    Upbit API를 사용하여 캔들 데이터를 조회합니다.
    
    Args:
        market (str): 마켓 코드 (예: KRW-BTC, KRW-ETH)
        interval (str): 캔들 간격 ('1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M')
        count (int): 조회할 캔들 개수 (최대 200개)
        to (str): 마지막 캔들 시각 (ISO 8601 형식)
    
    Returns:
        pd.DataFrame: 캔들 데이터 또는 None
    """
    
    # 간격에 따른 API 엔드포인트 결정
    if interval in ['1m', '3m', '5m', '15m', '30m']:
        endpoint = f"{UPBIT_BASE_URL}/candles/minutes/{interval[:-1]}"
    elif interval in ['1h', '4h']:
        endpoint = f"{UPBIT_BASE_URL}/candles/minutes/{int(interval[:-1]) * 60}"
    elif interval == '1d':
        endpoint = f"{UPBIT_BASE_URL}/candles/days"
    elif interval == '1w':
        endpoint = f"{UPBIT_BASE_URL}/candles/weeks"
    elif interval == '1M':
        endpoint = f"{UPBIT_BASE_URL}/candles/months"
    else:
        raise ValueError(f"지원하지 않는 간격입니다: {interval}")
    
    params = {
        'market': market,
        'count': min(count, 200)  # 최대 200개로 제한
    }
    
    if to:
        params['to'] = to
    
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        
        data = response.json()
        if not data:
            return None
        
        # DataFrame으로 변환
        df = pd.DataFrame(data)
        
        # 시간순으로 정렬 (오래된 것부터)
        df = df.sort_values('candle_date_time_utc').reset_index(drop=True)
        
        # candle_date_time_utc를 YYYYMMDDHHMM 형식으로 변환
        df['candle_date_time_utc'] = df['candle_date_time_utc'].apply(format_iso_to_datetime)
        
        return df
        
    except Exception as e:
        print(f"Upbit API 캔들 데이터 조회 실패: {e}")
        return None

def get_upbit_markets() -> List[str]:
    """
    Upbit에서 거래 가능한 모든 마켓 목록을 조회합니다.
    
    Returns:
        List[str]: 마켓 코드 리스트
    """
    try:
        url = f"{UPBIT_BASE_URL}/market/all"
        response = requests.get(url)
        response.raise_for_status()
        
        markets = response.json()
        return [market['market'] for market in markets if market['market'].startswith('KRW-')]
        
    except Exception as e:
        print(f"Upbit 마켓 목록 조회 실패: {e}")
        return []

##############################################################################################
# 캐시 및 DB 관련 함수들
##############################################################################################

def save_candle_data_to_cache(df: pd.DataFrame, market: str, interval: str):
    """
    캔들 데이터를 CSV 파일로 캐시에 저장합니다.
    
    Args:
        df (pd.DataFrame): 저장할 데이터
        market (str): 마켓 코드
        interval (str): 캔들 간격
    """
    filename = f"{market.replace('-', '_')}_candle_{interval}.csv"
    filepath = os.path.join(CRYPTO_CACHE_DIR, filename)
    
    try:
        df.to_csv(filepath, index=False)
        print(f"캔들 데이터가 캐시에 저장되었습니다: {filepath}")
    except Exception as e:
        print(f"캐시 저장 실패: {e}")

def load_candle_data_from_cache(market: str, interval: str) -> Optional[pd.DataFrame]:
    """
    캐시에서 캔들 데이터를 로드합니다.
    
    Args:
        market (str): 마켓 코드
        interval (str): 캔들 간격
    
    Returns:
        pd.DataFrame: 캐시된 데이터 또는 None
    """
    filename = f"{market.replace('-', '_')}_candle_{interval}.csv"
    filepath = os.path.join(CRYPTO_CACHE_DIR, filename)
    
    if not os.path.exists(filepath):
        return None
    
    try:
        df = pd.read_csv(filepath)
        return df
    except Exception as e:
        print(f"캐시 로드 실패: {e}")
        return None

def save_candle_data_to_db(df: pd.DataFrame, market: str, interval: str):
    """
    캔들 데이터를 데이터베이스에 저장합니다.
    
    Args:
        df (pd.DataFrame): 저장할 데이터
        market (str): 마켓 코드
        interval (str): 캔들 간격
    """
    try:
        table_name = f"crypto_candle_{market.replace('-', '_').lower()}_{interval}"
        
        # SQLite에서 안전한 테이블명으로 변환
        table_name = table_name.replace('-', '_')
        
        conn = sqlite3.connect(CRYPTO_DB_PATH)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.close()
        
        print(f"캔들 데이터가 DB에 저장되었습니다: {table_name}")
    except Exception as e:
        print(f"DB 저장 실패: {e}")

def load_candle_data_from_db(market: str, interval: str, start_datetime: str = None, end_datetime: str = None) -> Optional[pd.DataFrame]:
    """
    데이터베이스에서 캔들 데이터를 로드합니다.
    
    Args:
        market (str): 마켓 코드
        interval (str): 캔들 간격
        start_datetime (str): 시작 시간 (YYYYMMDDHHMM)
        end_datetime (str): 종료 시간 (YYYYMMDDHHMM)
    
    Returns:
        pd.DataFrame: 데이터베이스 데이터 또는 None
    """
    try:
        table_name = f"crypto_candle_{market.replace('-', '_').lower()}_{interval}"
        
        conn = sqlite3.connect(CRYPTO_DB_PATH)
        
        query = f"SELECT * FROM {table_name}"
        conditions = []
        
        if start_datetime:
            conditions.append(f"candle_date_time_utc >= '{start_datetime}'")
        if end_datetime:
            conditions.append(f"candle_date_time_utc <= '{end_datetime}'")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY candle_date_time_utc"
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df if not df.empty else None
        
    except Exception as e:
        print(f"DB 로드 실패: {e}")
        return None

##############################################################################################
# 메인 캔들 데이터 조회 함수
##############################################################################################

def get_candle_data(
    market: str,
    interval: str = '1m',
    start_datetime: str = None,
    end_datetime: str = None,
    use_cache: bool = True,
    force_api: bool = False
) -> Optional[pd.DataFrame]:
    """
    암호화폐 캔들 데이터를 조회합니다.
    
    Args:
        market (str): 마켓 코드 (예: KRW-BTC)
        interval (str): 캔들 간격 ('1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M')
        start_datetime (str): 시작 시간 (YYYYMMDDHHMM)
        end_datetime (str): 종료 시간 (YYYYMMDDHHMM)
        use_cache (bool): 캐시 사용 여부
        force_api (bool): 강제로 API 호출
    
    Returns:
        pd.DataFrame: 캔들 데이터
    """
    
    # 1. 강제 API 호출이 아니고 캐시 사용 시, 먼저 DB에서 확인
    if not force_api and use_cache:
        cached_data = load_candle_data_from_db(market, interval, start_datetime, end_datetime)
        if cached_data is not None and not cached_data.empty:
            print(f"DB에서 캔들 데이터 로드: {market} {interval}")
            return cached_data
    
    # 2. API에서 데이터 조회
    print(f"API에서 캔들 데이터 조회: {market} {interval}")
    
    all_data = []
    current_to = None
    
    # end_datetime가 지정된 경우 ISO 형식으로 변환
    if end_datetime:
        current_to = format_datetime_to_iso(end_datetime)
    
    # 데이터가 충분할 때까지 반복 조회
    max_iterations = 10  # 무한 루프 방지
    iteration = 0
    
    while iteration < max_iterations:
        df = get_upbit_candle_data(market, interval, count=200, to=current_to)
        
        if df is None or df.empty:
            break
        
        all_data.append(df)
        
        # start_datetime가 지정되었고, 충분한 데이터를 얻었으면 중단
        if start_datetime and df['candle_date_time_utc'].min() <= start_datetime:
            break
        
        # 다음 조회를 위한 to 값 설정 (가장 오래된 데이터의 시간)
        oldest_datetime = df['candle_date_time_utc'].min()
        current_to = format_datetime_to_iso(oldest_datetime)
        
        iteration += 1
        time.sleep(0.1)  # API 호출 제한 고려
    
    if not all_data:
        print(f"캔들 데이터를 조회할 수 없습니다: {market} {interval}")
        return None
    
    # 모든 데이터 합치기
    result_df = pd.concat(all_data, ignore_index=True)
    result_df = result_df.drop_duplicates(subset=['candle_date_time_utc']).sort_values('candle_date_time_utc').reset_index(drop=True)
    
    # 날짜 범위 필터링
    if start_datetime:
        result_df = result_df[result_df['candle_date_time_utc'] >= start_datetime]
    if end_datetime:
        result_df = result_df[result_df['candle_date_time_utc'] <= end_datetime]
    
    # 캐시 및 DB에 저장
    if use_cache and not result_df.empty:
        save_candle_data_to_cache(result_df, market, interval)
        save_candle_data_to_db(result_df, market, interval)
    
    return result_df

def get_latest_candle_data(market: str, interval: str = '1m', count: int = 100) -> Optional[pd.DataFrame]:
    """
    최신 캔들 데이터를 조회합니다.
    
    Args:
        market (str): 마켓 코드
        interval (str): 캔들 간격
        count (int): 조회할 캔들 개수
    
    Returns:
        pd.DataFrame: 최신 캔들 데이터
    """
    return get_upbit_candle_data(market, interval, count=count)

def get_all_krw_markets() -> List[str]:
    """
    KRW 기준 모든 마켓 목록을 조회합니다.
    
    Returns:
        List[str]: KRW 마켓 코드 리스트
    """
    return get_upbit_markets()

##############################################################################################
# 테스트 코드
##############################################################################################

if __name__ == "__main__":
    print("=== Crypto Data Manager 테스트 시작 ===\n")
    
    # 1. 마켓 목록 조회 테스트
    print("1. KRW 마켓 목록 조회 테스트")
    markets = get_all_krw_markets()
    print(f"총 {len(markets)}개 마켓 발견")
    print(f"처음 5개 마켓: {markets[:5]}\n")
    
    # 2. 최신 캔들 데이터 조회 테스트
    test_market = "KRW-BTC"
    print(f"2. 최신 캔들 데이터 조회 테스트 ({test_market})")
    
    latest_data = get_latest_candle_data(test_market, '1m', count=10)
    if latest_data is not None:
        print(f"데이터 shape: {latest_data.shape}")
        print("최신 5개 데이터:")
        print(latest_data.tail())
        print()
    else:
        print("최신 데이터 조회 실패\n")
    
    # 3. 특정 기간 캔들 데이터 조회 테스트
    print(f"3. 특정 기간 캔들 데이터 조회 테스트 ({test_market})")
    
    # 어제부터 오늘까지의 1분봉 데이터
    end_time = datetime.now()
    start_time = end_time - timedelta(days=1)
    
    start_datetime = start_time.strftime("%Y%m%d%H%M")
    end_datetime = end_time.strftime("%Y%m%d%H%M")
    
    print(f"조회 기간: {start_datetime} ~ {end_datetime}")
    
    period_data = get_candle_data(
        market=test_market,
        interval='1m',
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        use_cache=True,
        force_api=True
    )
    
    if period_data is not None:
        print(f"데이터 shape: {period_data.shape}")
        print("처음 5개 데이터:")
        print(period_data.head())
        print("\n마지막 5개 데이터:")
        print(period_data.tail())
        print()
    else:
        print("기간 데이터 조회 실패\n")
    
    # 4. 다양한 간격으로 테스트
    print("4. 다양한 간격 테스트")
    intervals = ['1m', '5m', '1h', '1d']
    
    for interval in intervals:
        print(f"  - {interval} 간격 테스트")
        data = get_latest_candle_data(test_market, interval, count=5)
        if data is not None:
            print(f"    데이터 개수: {len(data)}")
            print(f"    최신 가격: {data.iloc[-1]['trade_price']}")
        else:
            print("    데이터 조회 실패")
        time.sleep(0.1)  # API 호출 제한 고려
    
    print("\n=== 테스트 완료 ===")
