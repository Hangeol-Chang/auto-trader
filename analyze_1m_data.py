#!/usr/bin/env python3
"""
1분봉 데이터 로딩 실패 원인 분석 스크립트
"""

import sys
import os
from datetime import datetime, timedelta

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def analyze_time_format():
    """시간 형식 분석"""
    print("=== 시간 형식 분석 ===")
    
    now = datetime.now()
    start_time = now - timedelta(minutes=100)
    
    start_datetime = start_time.strftime('%Y%m%d%H%M')
    end_datetime = now.strftime('%Y%m%d%H%M')
    
    print(f"현재 시간: {now}")
    print(f"시작 시간: {start_time}")
    print(f"시작 datetime: {start_datetime}")
    print(f"종료 datetime: {end_datetime}")
    print()

def analyze_database():
    """데이터베이스 분석"""
    print("=== 데이터베이스 분석 ===")
    
    try:
        import sqlite3
        db_path = "data/crypto_data.db"
        
        if not os.path.exists(db_path):
            print(f"❌ 데이터베이스 파일이 존재하지 않음: {db_path}")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 테이블 목록 조회
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%krw_btc%';")
        tables = cursor.fetchall()
        
        print(f"KRW-BTC 관련 테이블: {tables}")
        
        # 1분봉 테이블 확인
        table_name = "crypto_candle_krw_btc_1m"
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print(f"✓ 1분봉 테이블 존재: {table_name}")
            
            # 데이터 개수 확인
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"  - 총 데이터 개수: {count}")
            
            # 최근 데이터 확인
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY candle_date_time_utc DESC LIMIT 5;")
            recent_data = cursor.fetchall()
            print(f"  - 최근 5개 데이터:")
            for row in recent_data:
                print(f"    {row}")
                
        else:
            print(f"❌ 1분봉 테이블이 존재하지 않음: {table_name}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 데이터베이스 분석 중 오류: {e}")
    
    print()

def analyze_api_call():
    """API 호출 분석"""
    print("=== API 호출 분석 ===")
    
    try:
        from module.crypto.crypto_data_manager import get_candle_data
        
        # 현재 시간 기준으로 1분봉 데이터 요청
        now = datetime.now()
        start_time = now - timedelta(minutes=100)
        
        start_datetime = start_time.strftime('%Y%m%d%H%M')
        end_datetime = now.strftime('%Y%m%d%H%M')
        
        print(f"요청 파라미터:")
        print(f"  - market: KRW-BTC")
        print(f"  - interval: 1m")
        print(f"  - start_datetime: {start_datetime}")
        print(f"  - end_datetime: {end_datetime}")
        print()
        
        # DB에서 먼저 시도
        print("1. DB에서 데이터 조회...")
        df_db = get_candle_data(
            market='KRW-BTC',
            interval='1m',
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            use_cache=True,
            force_api=False
        )
        
        print(f"DB 결과: {type(df_db)}, 길이: {len(df_db) if df_db is not None else 'None'}")
        
        # API에서 강제 조회
        print("2. API에서 데이터 조회...")
        df_api = get_candle_data(
            market='KRW-BTC',
            interval='1m',
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            use_cache=False,
            force_api=True
        )
        
        print(f"API 결과: {type(df_api)}, 길이: {len(df_api) if df_api is not None else 'None'}")
        
        # 결과 분석
        if df_api is not None and len(df_api) > 0:
            print(f"✓ API에서 데이터 조회 성공")
            print(f"  - 컬럼: {list(df_api.columns)}")
            print(f"  - 첫 번째 행:")
            print(f"    {df_api.iloc[0].to_dict()}")
        else:
            print(f"❌ API에서도 데이터 조회 실패")
            
    except Exception as e:
        print(f"❌ API 호출 분석 중 오류: {e}")
        import traceback
        traceback.print_exc()
    
    print()

def analyze_upbit_api_limits():
    """업비트 API 제한사항 분석"""
    print("=== 업비트 API 제한사항 분석 ===")
    
    print("업비트 API 특징:")
    print("1. 1분봉 데이터는 최대 200개까지만 조회 가능")
    print("2. 과거 데이터는 제한적")
    print("3. 실시간 데이터 위주로 제공")
    print("4. API 호출 제한: 초당 10회, 분당 600회")
    print()
    
    # 현재 시간 기준 가능한 범위 계산
    now = datetime.now()
    max_past_time = now - timedelta(minutes=200)  # 최대 200분 전
    
    print(f"현재 시간: {now}")
    print(f"1분봉 최대 조회 가능 시간: {max_past_time}")
    print(f"요청한 시간 범위: {now - timedelta(minutes=100)} ~ {now}")
    print("👍 요청 범위가 API 제한 내에 있음")
    print()

def main():
    """메인 분석 함수"""
    print("1분봉 데이터 로딩 실패 원인 분석")
    print("=" * 50)
    print()
    
    analyze_time_format()
    analyze_database()
    analyze_api_call()
    analyze_upbit_api_limits()
    
    print("=== 분석 완료 ===")
    print("추천 해결책:")
    print("1. 1분봉 대신 5분봉 또는 1시간봉 사용")
    print("2. force_api=True로 강제 API 호출")
    print("3. 더 짧은 시간 범위 요청 (예: 30분 전부터)")
    print("4. 실시간 웹소켓 데이터 활용")

if __name__ == "__main__":
    main()
