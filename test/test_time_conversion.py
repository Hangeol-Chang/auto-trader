#!/usr/bin/env python3
"""
crypto_data_manager 시간 형식 변환 테스트
"""

import sys
import os
from datetime import datetime, timedelta

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_time_conversion():
    """시간 형식 변환 테스트"""
    print("=== 시간 형식 변환 테스트 ===")
    
    # 실제 업비트 API 응답 시간 형식
    upbit_time = "2025-08-23T03:33:00"  # 실제 API에서 받은 형식
    
    def format_iso_to_datetime(iso_str: str) -> str:
        """crypto_data_manager의 변환 함수 복사"""
        iso_str = iso_str.replace('Z', '').split('+')[0].split('T')
        date_part = iso_str[0].replace('-', '')
        if len(iso_str) > 1:
            time_part = iso_str[1].replace(':', '')[:4]
            return date_part + time_part
        else:
            return date_part + "0000"
    
    converted = format_iso_to_datetime(upbit_time)
    print(f"업비트 시간: {upbit_time}")
    print(f"변환된 시간: {converted}")
    
    # 우리가 요청한 시간 범위
    now = datetime.now()
    start_time = now - timedelta(minutes=100)
    start_datetime = start_time.strftime('%Y%m%d%H%M')
    end_datetime = now.strftime('%Y%m%d%H%M')
    
    print(f"요청 시작 시간: {start_datetime}")
    print(f"요청 종료 시간: {end_datetime}")
    print(f"변환된 시간: {converted}")
    
    # 범위 체크
    if start_datetime <= converted <= end_datetime:
        print("✓ 변환된 시간이 요청 범위 내에 있음")
    else:
        print(f"❌ 변환된 시간이 요청 범위 밖에 있음")
        print(f"  시작: {start_datetime}")
        print(f"  변환: {converted}")  
        print(f"  종료: {end_datetime}")

def test_get_upbit_candle_data():
    """get_upbit_candle_data 함수 직접 테스트"""
    print("\n=== get_upbit_candle_data 함수 테스트 ===")
    
    try:
        from module.crypto.crypto_data_manager import get_upbit_candle_data
        
        # 직접 API 호출
        df = get_upbit_candle_data('KRW-BTC', '1m', count=10)
        
        if df is not None and len(df) > 0:
            print(f"✓ API 호출 성공: {len(df)}개 데이터")
            print("컬럼:", list(df.columns))
            print("첫 번째 행:", df.iloc[0]['candle_date_time_utc'])
            print("마지막 행:", df.iloc[-1]['candle_date_time_utc'])
        else:
            print("❌ API 호출 실패 또는 빈 데이터")
            
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

def test_full_get_candle_data():
    """전체 get_candle_data 함수 테스트"""
    print("\n=== 전체 get_candle_data 함수 테스트 ===")
    
    try:
        from module.crypto.crypto_data_manager import get_candle_data
        
        # 현재 시간 기준
        now = datetime.now()
        start_time = now - timedelta(minutes=30)  # 더 짧은 범위로 테스트
        
        start_datetime = start_time.strftime('%Y%m%d%H%M')
        end_datetime = now.strftime('%Y%m%d%H%M')
        
        print(f"테스트 범위: {start_datetime} ~ {end_datetime}")
        
        # force_api=True로 강제 API 호출
        df = get_candle_data(
            market='KRW-BTC',
            interval='1m',
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            use_cache=False,
            force_api=True
        )
        
        if df is not None and len(df) > 0:
            print(f"✓ 전체 함수 성공: {len(df)}개 데이터")
            print("시간 범위:")
            print(f"  최소: {df['candle_date_time_utc'].min()}")
            print(f"  최대: {df['candle_date_time_utc'].max()}")
        else:
            print("❌ 전체 함수 실패 또는 빈 데이터")
            
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_time_conversion()
    test_get_upbit_candle_data()  
    test_full_get_candle_data()
