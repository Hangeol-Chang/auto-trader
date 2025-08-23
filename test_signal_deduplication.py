#!/usr/bin/env python3
"""
신호 중복 방지 로직 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_signal_deduplication():
    """신호 중복 방지 로직 테스트"""
    
    # Live_Crypto_Trader의 신호 중복 방지 메서드만 테스트
    class MockTrader:
        def __init__(self):
            self._last_actions = {}
        
        def _should_skip_signal(self, market, action):
            """
            신호 중복 방지 검사
            - 마지막 액션이 BUY였다면, SELL 신호가 올 때까지 BUY 신호 무시
            - 마지막 액션이 SELL이었다면, BUY 신호가 올 때까지 SELL 신호 무시
            """
            if market not in self._last_actions:
                return False  # 첫 번째 신호는 허용
            
            last_action = self._last_actions[market]
            
            # 같은 액션이 연속으로 발생하는 경우 스킵
            if last_action == action:
                print(f"[{market}] 중복 신호 스킵: {action} (마지막 액션: {last_action})")
                return True
            
            return False  # 다른 액션인 경우 허용
        
        def _update_last_action(self, market, action, success=True):
            """
            마지막 액션 업데이트
            - success=True: 주문이 성공한 경우에만 업데이트
            - success=False: 주문이 실패한 경우 업데이트하지 않음 (재시도 가능하도록)
            """
            if success:
                self._last_actions[market] = action
                print(f"[{market}] 마지막 액션 업데이트: {action}")
            else:
                print(f"[{market}] 주문 실패로 인한 마지막 액션 유지: {self._last_actions.get(market, 'None')}")
    
    trader = MockTrader()
    market = "KRW-BTC"
    
    print("=== 신호 중복 방지 로직 테스트 ===\n")
    
    # 테스트 케이스 1: 첫 번째 BUY 신호
    print("1. 첫 번째 BUY 신호")
    should_skip = trader._should_skip_signal(market, "BUY")
    print(f"   스킵 여부: {should_skip}")
    print(f"   예상: False (첫 번째 신호는 허용)")
    trader._update_last_action(market, "BUY", success=True)
    print(f"   현재 마지막 액션: {trader._last_actions.get(market)}\n")
    
    # 테스트 케이스 2: 연속된 BUY 신호 (중복)
    print("2. 연속된 BUY 신호 (중복)")
    should_skip = trader._should_skip_signal(market, "BUY")
    print(f"   스킵 여부: {should_skip}")
    print(f"   예상: True (중복 신호 스킵)\n")
    
    # 테스트 케이스 3: SELL 신호 (허용)
    print("3. SELL 신호 (허용)")
    should_skip = trader._should_skip_signal(market, "SELL")
    print(f"   스킵 여부: {should_skip}")
    print(f"   예상: False (다른 액션이므로 허용)")
    trader._update_last_action(market, "SELL", success=True)
    print(f"   현재 마지막 액션: {trader._last_actions.get(market)}\n")
    
    # 테스트 케이스 4: 연속된 SELL 신호 (중복)
    print("4. 연속된 SELL 신호 (중복)")
    should_skip = trader._should_skip_signal(market, "SELL")
    print(f"   스킵 여부: {should_skip}")
    print(f"   예상: True (중복 신호 스킵)\n")
    
    # 테스트 케이스 5: 다시 BUY 신호 (허용)
    print("5. 다시 BUY 신호 (허용)")
    should_skip = trader._should_skip_signal(market, "BUY")
    print(f"   스킵 여부: {should_skip}")
    print(f"   예상: False (다른 액션이므로 허용)")
    trader._update_last_action(market, "BUY", success=True)
    print(f"   현재 마지막 액션: {trader._last_actions.get(market)}\n")
    
    # 테스트 케이스 6: 주문 실패 시나리오
    print("6. 주문 실패 시나리오")
    print(f"   현재 마지막 액션: {trader._last_actions.get(market)}")
    trader._update_last_action(market, "SELL", success=False)
    print(f"   실패 후 마지막 액션: {trader._last_actions.get(market)}")
    print(f"   예상: BUY (실패시 액션 유지)")
    
    # 다음 신호 테스트
    should_skip = trader._should_skip_signal(market, "SELL")
    print(f"   다음 SELL 신호 스킵 여부: {should_skip}")
    print(f"   예상: False (마지막 액션이 BUY이므로 SELL 허용)\n")
    
    print("=== 테스트 완료 ===")

if __name__ == "__main__":
    test_signal_deduplication()
