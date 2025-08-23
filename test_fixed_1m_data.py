#!/usr/bin/env python3
"""
수정된 crypto_data_manager 테스트
"""

import sys
import os
from datetime import datetime, timedelta

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_fixed_get_candle_data():
    """수정된 get_candle_data 함수 테스트"""
    print("=== 수정된 get_candle_data 함수 테스트 ===")
    
    from module.crypto.crypto_data_manager import get_candle_data
    
    # 현재 한국 시간 기준
    now = datetime.now()
    start_time = now - timedelta(hours=1)  # 1시간 전부터
    
    start_datetime_kst = start_time.strftime('%Y%m%d%H%M')
    end_datetime_kst = now.strftime('%Y%m%d%H%M')
    
    print(f"한국 시간으로 요청: {start_datetime_kst} ~ {end_datetime_kst}")
    
    # 수정된 함수로 테스트
    df = get_candle_data(
        market='KRW-BTC',
        interval='1m',
        start_datetime=start_datetime_kst,
        end_datetime=end_datetime_kst,
        use_cache=False,
        force_api=True
    )
    
    if df is not None and len(df) > 0:
        print(f"✅ 수정 후 성공: {len(df)}개 데이터")
        print(f"시간 범위: {df['candle_date_time_utc'].min()} ~ {df['candle_date_time_utc'].max()}")
        
        # 첫 번째와 마지막 몇 개 행 확인
        print(f"\n첫 5개 데이터:")
        print(df[['candle_date_time_utc', 'trade_price']].head())
        print(f"\n마지막 5개 데이터:")
        print(df[['candle_date_time_utc', 'trade_price']].tail())
        
    else:
        print("❌ 수정 후에도 실패")

def test_live_crypto_trader():
    """Live_Crypto_Trader에서 1분봉 로딩 테스트"""
    print("\n=== Live_Crypto_Trader 1분봉 로딩 테스트 ===")
    
    try:
        from core.trader import Live_Crypto_Trader
        
        print("Live_Crypto_Trader 초기화 중...")
        trader = Live_Crypto_Trader(
            market='KRW-BTC',
            model_path='model/crypto_rl_models',
            api_keys_path='private/keys.json'
        )
        
        print("✅ Live_Crypto_Trader 초기화 성공")
        
        # 1분봉 데이터 로딩 테스트
        print("\n1분봉 데이터 로딩 테스트...")
        market_data = trader._initialize_market_data()
        
        if market_data is not None and len(market_data) > 0:
            print(f"✅ 1분봉 로딩 성공: {len(market_data)}개 데이터")
            print(f"시간 범위: {market_data.index.min()} ~ {market_data.index.max()}")
        else:
            print("❌ 1분봉 로딩 실패")
            
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fixed_get_candle_data()
    test_live_crypto_trader()
