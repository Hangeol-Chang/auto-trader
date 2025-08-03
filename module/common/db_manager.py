import sqlite3
import pandas as pd
from datetime import datetime
import os

DATA_DIR = "data"
DB_PATH = os.path.join(DATA_DIR, "stock_data.db")
# 날짜 관련
os.makedirs(DATA_DIR, exist_ok=True)

##############################################################################################
# 데이터 저장 관련 로직 (SQLite)
##############################################################################################
def _init_database():
    """데이터베이스 및 테이블 초기화"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # 거래일 정보 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trading_days (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    country_code TEXT NOT NULL,
                    year TEXT NOT NULL,
                    date TEXT NOT NULL,
                    UNIQUE(country_code, year, date)
                )
            ''')
            
            # 주식 가격 데이터 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_price_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    country_code TEXT NOT NULL,
                    date TEXT NOT NULL,
                    period_code TEXT NOT NULL DEFAULT 'D',
                    api_name TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    amount REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker, date, period_code, api_name)
                )
            ''')
            
            # 처리된 데이터 테이블 (MACD, 볼린저 밴드 등)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    date TEXT NOT NULL,
                    period_code TEXT NOT NULL DEFAULT 'D',
                    close REAL,
                    center REAL,
                    upper_band REAL,
                    lower_band REAL,
                    macd REAL,
                    macd_signal REAL,
                    macd_histogram REAL,
                    sma_short REAL,
                    sma_long REAL,
                    bf_1m_close REAL,
                    bf_12m_close REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker, date, period_code)
                )
            ''')
            
            # 종목 정보 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ticker_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL UNIQUE,
                    name TEXT,
                    market TEXT,
                    market_cap REAL,
                    shares INTEGER,
                    close_price REAL,
                    bps REAL,
                    per REAL,
                    pbr REAL,
                    eps REAL,
                    dividend_yield REAL,
                    dps REAL,
                    sector TEXT,
                    trading_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            print("데이터베이스 테이블이 초기화되었습니다.")
    except Exception as e:
        print(f"데이터베이스 초기화 실패: {e}")

def save_trading_days_to_db(trading_days, year, country_code):
    """거래일 정보를 데이터베이스에 저장"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # 기존 데이터 삭제
            cursor.execute(
                "DELETE FROM trading_days WHERE country_code = ? AND year = ?",
                (country_code, year)
            )
            
            # 새 데이터 삽입
            data_to_insert = [
                (country_code, year, d.strftime("%Y%m%d"))
                for d in trading_days
            ]
            
            cursor.executemany(
                "INSERT OR REPLACE INTO trading_days (country_code, year, date) VALUES (?, ?, ?)",
                data_to_insert
            )
            
            conn.commit()
            print(f"거래일 데이터가 데이터베이스에 저장되었습니다: {country_code} {year}")
    except Exception as e:
        print(f"거래일 데이터 저장 실패: {e}")

def load_trading_days_from_db(year, country_code):
    """데이터베이스에서 거래일 정보 로드"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query(
                "SELECT date FROM trading_days WHERE country_code = ? AND year = ? ORDER BY date",
                conn,
                params=(country_code, year)
            )
            
            if not df.empty:
                trading_days = [datetime.strptime(d, "%Y%m%d") for d in df['date']]
                return trading_days
            return []
    except Exception as e:
        print(f"거래일 데이터 로드 실패: {e}")
        return []

def check_date_exists_in_db(ticker, target_date, period_code='D', api_name='itemchartprice_history'):
    """데이터베이스에서 특정 날짜 데이터 존재 여부 확인"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM stock_price_data WHERE ticker = ? AND date = ? AND period_code = ? AND api_name = ?",
                (ticker, target_date, period_code, api_name)
            )
            count = cursor.fetchone()[0]
            return count > 0
    except Exception as e:
        print(f"날짜 존재 확인 중 오류: {e}")
        return False

def load_existing_data_from_db(ticker, start_date=None, end_date=None, period_code='D', api_name='itemchartprice_history'):
    """데이터베이스에서 기존 데이터 로드"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            query = """
                SELECT ticker, date, period_code, open, high, low, close, volume, amount
                FROM stock_price_data 
                WHERE ticker = ? AND period_code = ? AND api_name = ?
            """
            params = [ticker, period_code, api_name]
            
            if start_date and end_date:
                query += " AND date BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            
            query += " ORDER BY date"
            
            df = pd.read_sql_query(query, conn, params=params)
            return df
    except Exception as e:
        print(f"기존 데이터 로드 실패: {e}")
        return pd.DataFrame()

def save_data_to_db(dataframe, ticker, country_code, period_code='D', api_name='itemchartprice_history'):
    """데이터를 데이터베이스에 저장"""
    try:
        _init_database()
        
        with sqlite3.connect(DB_PATH) as conn:
            # 데이터프레임에 메타데이터 추가
            df_to_save = dataframe.copy()
            df_to_save['ticker'] = ticker
            df_to_save['country_code'] = country_code
            df_to_save['period_code'] = period_code
            df_to_save['api_name'] = api_name
            
            # 필요한 컬럼들이 없으면 None으로 추가
            required_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
            for col in required_cols:
                if col not in df_to_save.columns:
                    df_to_save[col] = None
            
            # 데이터베이스에 저장 (중복 시 업데이트)
            df_to_save.to_sql('temp_stock_data', conn, if_exists='replace', index=False)
            
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO stock_price_data 
                (ticker, country_code, date, period_code, api_name, open, high, low, close, volume, amount, updated_at)
                SELECT ticker, country_code, date, period_code, api_name, open, high, low, close, volume, amount, CURRENT_TIMESTAMP
                FROM temp_stock_data
            ''')
            
            cursor.execute('DROP TABLE temp_stock_data')
            conn.commit()
            
            print(f"데이터가 데이터베이스에 저장되었습니다: {ticker} ({len(dataframe)} 행)")
    except Exception as e:
        print(f"데이터베이스 저장 실패: {e}")

def save_ticker_info_to_db(dataframe):
    """종목 정보를 데이터베이스에 저장"""
    try:
        _init_database()
        
        with sqlite3.connect(DB_PATH) as conn:
            # 데이터베이스에 저장 (중복 시 업데이트)
            dataframe.to_sql('temp_ticker_info', conn, if_exists='replace', index=False)
            
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO ticker_info 
                (ticker, name, market, market_cap, shares, close_price, bps, per, pbr, eps, 
                 dividend_yield, dps, sector, trading_date, updated_at)
                SELECT ticker, name, market, market_cap, shares, close_price, bps, per, pbr, eps,
                       dividend_yield, dps, sector, trading_date, CURRENT_TIMESTAMP
                FROM temp_ticker_info
            ''')
            
            cursor.execute('DROP TABLE temp_ticker_info')
            conn.commit()
            
            print(f"종목 정보가 데이터베이스에 저장되었습니다: {len(dataframe)} 행")
    except Exception as e:
        print(f"종목 정보 저장 실패: {e}")

def load_ticker_info_from_db():
    """데이터베이스에서 종목 정보 로드"""
    try:
        _init_database()
        
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query("SELECT * FROM ticker_info ORDER BY ticker", conn)
            return df
    except Exception as e:
        print(f"종목 정보 로드 실패: {e}")
        return pd.DataFrame()
    
##############################################################################################
# 데이터베이스 초기화 (모듈 로드 시 실행)
##############################################################################################
def _ensure_database_initialized():
    """데이터베이스가 초기화되지 않았다면 초기화"""
    if not os.path.exists(DB_PATH):
        _init_database()

# 모듈 로드 시 데이터베이스 초기화 확인
try:
    _ensure_database_initialized()
except:
    # 초기화 실패 시 무시하고 계속 (필요할 때 다시 시도)
    pass