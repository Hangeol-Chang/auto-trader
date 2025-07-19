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

import pandas as pd
import os
from datetime import datetime, timedelta
from pykrx import stock

import module.kis_fetcher as kis_fetcher
import module.column_mapper as column_mapper


DATA_DIR = "data"
# 날짜 관련
os.makedirs(DATA_DIR, exist_ok=True)

# 연도별 개장일 정보를 메모리 캐시에 저장하여 반복적인 로딩을 방지합니다.
_TRADING_DAY_CACHE = {}

def get_trading_days(year: str) -> list:
    """
    특정 연도의 모든 개장일을 CSV 파일 또는 pykrx에서 불러와 리스트로 반환합니다.
    """
    if year in _TRADING_DAY_CACHE:
        return _TRADING_DAY_CACHE[year]

    file_path = os.path.join(DATA_DIR, f"TRADING_DATE_{year}.csv")

    # 날짜가 올해면 API 호출
    if datetime.now().year == int(year):
        try:
            df = stock.get_market_ohlcv(f"{year}0101", f"{year}1231", "005930")
            trading_days = df.index.to_list()
            # CSV 파일로 저장
            df_to_save = pd.DataFrame({'date': [d.strftime("%Y%m%d") for d in trading_days]})
            df_to_save.to_csv(file_path, index=False)
            _TRADING_DAY_CACHE[year] = trading_days
            return trading_days
        
        except Exception as e:
            print(f"[오류] pykrx에서 {year} 데이터 조회 실패: {e}")
            return []

    if os.path.exists(file_path):
        # CSV 파일에서 개장일 불러오기
        try:
            df = pd.read_csv(file_path)
            trading_days = [datetime.strptime(d, "%Y%m%d") for d in df['date']]
            _TRADING_DAY_CACHE[year] = trading_days
            return trading_days
        except Exception as e:
            print(f"[오류] {file_path} 읽기 실패: {e}")
            return []
    else:
        # pykrx API 호출하여 개장일 조회
        try:
            df = stock.get_market_ohlcv(f"{year}0101", f"{year}1231", "005930")
            trading_days = df.index.to_list()

            # CSV 파일로 저장
            df_to_save = pd.DataFrame({'date': [d.strftime("%Y%m%d") for d in trading_days]})
            df_to_save.to_csv(file_path, index=False)
            _TRADING_DAY_CACHE[year] = trading_days
            return trading_days
        
        except Exception as e:
            print(f"[오류] pykrx에서 {year} 데이터 조회 실패: {e}")
            return []

def get_next_trading_day(base_date) -> str:
    """
    다음 거래일을 반환합니다.
    
    Args:
        base_date: 기준일 (str "YYYYMMDD" 형식 또는 int YYYYMMDD)
        
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
        trading_days = get_trading_days(str(year))
        future_days = [d for d in trading_days if d > base_date]
        if future_days:
            return future_days[0].strftime("%Y%m%d")
        year += 1

def get_previous_trading_day(base_date) -> str:
    """
    이전 거래일을 반환합니다.
    
    Args:
        base_date: 기준일 (str "YYYYMMDD" 형식 또는 int YYYYMMDD)
        
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
        trading_days = get_trading_days(str(year))
        past_days = [d for d in trading_days if d < base_date]
        if past_days:
            return past_days[-1].strftime("%Y%m%d")
        year -= 1


def get_trading_days_in_range(start_date_str: str, end_date_str: str) -> list:
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

    trading_days = []
    for year in range(start_date.year, end_date.year + 1):
        year_days = get_trading_days(str(year))
        trading_days.extend(year_days)

    # 범위 내로 필터링
    filtered_days = [d for d in trading_days if start_date <= d <= end_date]
    return sorted(filtered_days)

################################################
# 데이터 저장 관련 로직
## CSV 데이터 저장 디렉토리 설정

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

def _get_csv_filepath(filename):
    """CSV 파일의 전체 경로 반환"""
    return os.path.join(DATA_DIR, filename)

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
    # 두 데이터프레임 모두 날짜 컬럼을 문자열로 통일
    if existing_data is not None:
        existing_data[date_column] = existing_data[date_column].astype(str)
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

    # Convert KIS column names to my_app format with dual header (Korean + my_app)
    dataframe = column_mapper.convert_dataframe_columns(current_data, as_is="kis", to_be="my_app")

    return dataframe

##############################################################################################
# [국내주식] 기본시세 > 국내주식기간별시세(일/주/월/년)
# 국내주식기간별시세(일/주/월/년) API입니다.d
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
    if start_date is None:
        start_date = (datetime.now()-timedelta(days=14)).strftime("%Y%m%d")   # 시작일자 값이 없으면 현재일자
    if  end_date is None:
        end_date  = datetime.today().strftime("%Y%m%d")   # 종료일자 값이 없으면 현재일자

    start_date = get_next_trading_day(start_date)
    end_date = get_previous_trading_day(end_date)

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
        itm_no="",      # 종목번호 (6자리) ETN의 경우, Q로 시작 (EX. Q500001)
        tr_cont="",     # 트랜잭션 내용 (선택사항)
        start_date=None, 
        end_date=None, 
        period_code="D", 
        adj_prc="1", 
        dataframe=None
):  
    # [국내주식] 기본시세 > 국내주식기간별시세(일/주/월/년)
    
    # CSV 파일명 생성 (API 이름에 output2를 추가해 구분)
    csv_filename = _generate_csv_filename(itm_no, "itemchartprice_history", period_code)
    csv_filepath = _get_csv_filepath(csv_filename)
    
    # 기존 데이터 로드
    existing_data = _load_existing_data(csv_filepath)

    if start_date is None:
        start_date = (datetime.now()-timedelta(days=14)).strftime("%Y%m%d")   # 시작일자 값이 없으면 2주 전 일자
    if  end_date is None:
        end_date  = datetime.today().strftime("%Y%m%d")   # 종료일자 값이 없으면 현재일자

    start_date = get_next_trading_day(start_date)
    end_date = get_previous_trading_day(end_date)

    _ori_start_date = start_date
    _ori_end_date = end_date

    print(f"조회 기간: {start_date} ~ {end_date}")
    
    # 요청된 날짜 범위의 데이터가 이미 있는지 확인
    if existing_data is not None and not existing_data.empty:
        # 기존 데이터에서 요청한 날짜 범위의 데이터가 모두 있는지 확인
        date_list = get_trading_days_in_range(start_date, end_date)
        blank_dates = []
        for date in date_list:
            if not _check_date_exists_in_data(existing_data, date):
                blank_dates.append(date)

        # 모든 데이터가 존재하면
        if blank_dates == []:
            print(f"캐시된 데이터를 사용합니다: {csv_filename}")
            # 요청한 날짜 범위의 데이터만 필터링해서 반환
            try:
                existing_data['date'] = pd.to_datetime(existing_data['date'], format='%Y%m%d', errors='coerce')
                start_dt = pd.to_datetime(start_date, format='%Y%m%d')
                end_dt = pd.to_datetime(end_date, format='%Y%m%d')
                filtered_data = existing_data[
                    (existing_data['date'] >= start_dt) & 
                    (existing_data['date'] <= end_dt)
                ].copy()
                return filtered_data
            except Exception as e:
                print(f"데이터 필터링 중 오류: {e}")

        start_date = blank_dates[0]  # 첫 번째 빈 날짜로 시작일을 조정
        end_date = blank_dates[-1]    # 마지막 빈 날짜로 종료일을 조정

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

    # output2: 기간별 OHLCV 히스토리 데이터 (차트 분석용)
    current_data = pd.DataFrame(res.getBody().output2)  # 기간별 일봉 데이터

    # Convert KIS column names to my_app format with dual header (Korean + my_app)
    dataframe = column_mapper.convert_dataframe_columns(current_data, as_is="kis", to_be="my_app")

    # 새로운 데이터를 CSV에 저장 (기존 데이터와 병합)
    result_data = _merge_and_save_data(existing_data, dataframe, csv_filepath)

    # _ori_start_date와 _ori_end_date를 사용하여 원래 요청한 날짜 범위로 필터링
    try:
        result_data['date'] = pd.to_datetime(result_data['date'], format='%Y%m%d', errors='coerce')
        start_dt = pd.to_datetime(_ori_start_date, format='%Y%m%d')
        end_dt = pd.to_datetime(_ori_end_date, format='%Y%m%d')
        result_data = result_data[
            (result_data['date'] >= start_dt) & 
            (result_data['date'] <= end_dt)
        ].copy()
    except Exception as e:
        print(f"데이터 필터링 중 오류: {e}")

    return result_data