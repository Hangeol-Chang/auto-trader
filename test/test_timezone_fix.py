#!/usr/bin/env python3
"""
시간대 문제 해결 테스트
"""

import sys
import os
from datetime import datetime, timedelta

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_timezone_issue():
    """시간대 문제 분석"""
    print("=== 시간대 문제 분석 ===")
    
    from module.crypto.crypto_data_manager import get_candle_data
    
    # 현재 시간 (한국 시간)
    now = datetime.now()
    start_time_kst = now - timedelta(hours=2)  # 2시간 전부터
    
    start_datetime_kst = start_time_kst.strftime('%Y%m%d%H%M')
    end_datetime_kst = now.strftime('%Y%m%d%H%M')
    
    print(f"한국 시간 범위: {start_datetime_kst} ~ {end_datetime_kst}")
    
    # UTC 시간으로 변환 (9시간 빼기)
    start_time_utc = start_time_kst - timedelta(hours=9)
    end_time_utc = now - timedelta(hours=9)
    
    start_datetime_utc = start_time_utc.strftime('%Y%m%d%H%M')
    end_datetime_utc = end_time_utc.strftime('%Y%m%d%H%M')
    
    print(f"UTC 시간 범위: {start_datetime_utc} ~ {end_datetime_utc}")
    
    # UTC 시간으로 테스트
    print("\n--- UTC 시간으로 요청 ---")
    df_utc = get_candle_data(
        market='KRW-BTC',
        interval='1m', 
        start_datetime=start_datetime_utc,
        end_datetime=end_datetime_utc,
        use_cache=False,
        force_api=True
    )
    
    if df_utc is not None and len(df_utc) > 0:
        print(f"✓ UTC 시간 요청 성공: {len(df_utc)}개 데이터")
        print(f"시간 범위: {df_utc['candle_date_time_utc'].min()} ~ {df_utc['candle_date_time_utc'].max()}")
    else:
        print("❌ UTC 시간 요청 실패")
    
    # 한국 시간으로 테스트 
    print("\n--- 한국 시간으로 요청 ---")
    df_kst = get_candle_data(
        market='KRW-BTC',
        interval='1m',
        start_datetime=start_datetime_kst,
        end_datetime=end_datetime_kst,
        use_cache=False,
        force_api=True
    )
    
    if df_kst is not None and len(df_kst) > 0:
        print(f"✓ 한국 시간 요청 성공: {len(df_kst)}개 데이터")
        print(f"시간 범위: {df_kst['candle_date_time_utc'].min()} ~ {df_kst['candle_date_time_utc'].max()}")
    else:
        print("❌ 한국 시간 요청 실패")

def test_no_time_filter():
    """시간 필터 없이 테스트"""
    print("\n=== 시간 필터 없이 테스트 ===")
    
    from module.crypto.crypto_data_manager import get_candle_data
    
    # 시간 범위 없이 최신 데이터만 요청
    df = get_candle_data(
        market='KRW-BTC',
        interval='1m',
        start_datetime=None,
        end_datetime=None,
        use_cache=False,
        force_api=True
    )
    
    if df is not None and len(df) > 0:
        print(f"✓ 시간 필터 없이 성공: {len(df)}개 데이터")
        print(f"시간 범위: {df['candle_date_time_utc'].min()} ~ {df['candle_date_time_utc'].max()}")
    else:
        print("❌ 시간 필터 없이도 실패")

if __name__ == "__main__":
    test_timezone_issue()
    test_no_time_filter()
