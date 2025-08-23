#!/usr/bin/env python3
"""
잔고 기반 초기 상태 설정 테스트 스크립트
"""
import sys
import os
import time
from datetime import datetime

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.trader import Live_Crypto_Trader

def test_balance_initialization():
    """잔고 기반 초기 상태 설정 테스트"""
    print("=" * 50)
    print("잔고 기반 초기 상태 설정 테스트 시작")
    print("=" * 50)
    
    try:
        # 실제 API 키를 사용하여 Live_Crypto_Trader 초기화
        # 주요 코인들 대상으로 테스트
        markets = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
        
        print(f"\n모니터링 대상 마켓: {markets}")
        print("\nLive_Crypto_Trader 초기화 중...")
        
        trader = Live_Crypto_Trader(
            markets=markets,
            interval='1m'
        )
        
        print("\n초기화 완료!")
        print("\n현재 매수/매도 상태:")
        print("-" * 30)
        
        for market in markets:
            if market in trader._last_actions:
                status = "매수 상태" if trader._last_actions[market] == 'BUY' else "매도 상태"
                print(f"{market}: {status}")
            else:
                print(f"{market}: 매도 상태 (미보유)")
                
        print("\n테스트 완료!")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_balance_initialization()
