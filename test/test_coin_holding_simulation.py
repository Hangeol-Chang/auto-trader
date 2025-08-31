#!/usr/bin/env python3
"""
잔고 기반 초기 상태 설정 시뮬레이션 테스트
(코인 보유 시나리오 포함)
"""
import sys
import os
from unittest.mock import Mock, patch

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.trader import Live_Crypto_Trader

def simulate_coin_holdings():
    """코인 보유 시나리오를 시뮬레이션"""
    print("=" * 50)
    print("코인 보유 시나리오 시뮬레이션")
    print("=" * 50)
    
    # 시뮬레이션할 잔고 데이터
    # 총 자산 200만원 상당 (KRW 100만원 + BTC 50만원 + ETH 30만원 + XRP 20만원)
    mock_balances = [
        {'currency': 'KRW', 'balance': '1000000', 'locked': '0', 'avg_buy_price': '0', 'avg_buy_price_modified': True, 'unit_currency': 'KRW'},
        {'currency': 'BTC', 'balance': '0.005', 'locked': '0', 'avg_buy_price': '100000000', 'avg_buy_price_modified': True, 'unit_currency': 'KRW'},
        {'currency': 'ETH', 'balance': '0.1', 'locked': '0', 'avg_buy_price': '3000000', 'avg_buy_price_modified': True, 'unit_currency': 'KRW'},
        {'currency': 'XRP', 'balance': '300', 'locked': '0', 'avg_buy_price': '700', 'avg_buy_price_modified': True, 'unit_currency': 'KRW'},
    ]
    
    # 현재가 시뮬레이션 (BTC=1억원, ETH=300만원, XRP=700원)
    def mock_get_current_price(market):
        prices = {
            'KRW-BTC': 100000000,  # 1억원 (0.005 * 1억 = 50만원, 25%)
            'KRW-ETH': 3000000,    # 300만원 (0.1 * 300만 = 30만원, 15%)
            'KRW-XRP': 700,        # 700원 (300 * 700 = 21만원, 10.5%)
        }
        return prices.get(market)
    
    try:
        markets = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
        print(f"모니터링 대상 마켓: {markets}")
        print(f"시뮬레이션 잔고:")
        print(f"  - KRW: 1,000,000원")
        print(f"  - BTC: 0.005개 (예상 가치: 500,000원, 25%)")
        print(f"  - ETH: 0.1개 (예상 가치: 300,000원, 15%)")
        print(f"  - XRP: 300개 (예상 가치: 210,000원, 10.5%)")
        print(f"  - 총 자산: 2,010,000원")
        print(f"  - 5% 임계값: 100,500원")
        print(f"  → BTC, ETH, XRP 모두 매수 상태로 초기화될 예정")
        print()
        
        # Live_Crypto_Trader 초기화
        trader = Live_Crypto_Trader(markets=markets, interval='1m')
        
        # upbit_api 메서드 모킹
        trader.orderer.upbit_api.get_balances = Mock(return_value=mock_balances)
        trader.orderer.upbit_api.get_current_price = Mock(side_effect=mock_get_current_price)
        
        # 초기 상태 재설정
        print("잔고 기반 초기 상태 재설정 중...")
        trader._initialize_trading_states()
        
        print("\n" + "="*30)
        print("시뮬레이션 결과:")
        print("="*30)
        
        for market in markets:
            if market in trader._last_actions:
                status = "매수 상태" if trader._last_actions[market] == 'BUY' else "매도 상태"
                print(f"{market}: {status}")
            else:
                print(f"{market}: 매도 상태 (미보유)")
                
        print("\n시뮬레이션 완료!")
        
        # 결과 검증
        expected_buy_states = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP']
        actual_buy_states = [market for market, action in trader._last_actions.items() if action == 'BUY']
        
        print(f"\n예상 매수 상태: {expected_buy_states}")
        print(f"실제 매수 상태: {actual_buy_states}")
        
        if set(expected_buy_states) == set(actual_buy_states):
            print("✅ 시뮬레이션 성공: 모든 코인이 예상대로 매수 상태로 설정되었습니다!")
        else:
            print("❌ 시뮬레이션 실패: 예상과 다른 결과입니다.")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simulate_coin_holdings()
