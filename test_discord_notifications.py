#!/usr/bin/env python3
"""
Discord 알림 기능 테스트 스크립트
"""
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.trader import Live_Crypto_Trader

def test_discord_notifications():
    """Discord 알림 기능 테스트"""
    print("=" * 50)
    print("Discord 알림 기능 테스트")
    print("=" * 50)
    
    try:
        # Live_Crypto_Trader 초기화
        markets = ["KRW-BTC"]
        trader = Live_Crypto_Trader(markets=markets, interval='1m')
        
        print("1. 주문 신호 Discord 알림 테스트")
        print("-" * 30)
        
        # 주문 신호 테스트 데이터
        order_signal_data = {
            'action': 'BUY',
            'market': 'KRW-BTC',
            'confidence': 0.85,
            'current_price': 95000000,+
            'amount_krw': 10000,
            'timestamp': datetime.now().isoformat(),
            'reason': '강력한 상승 신호 감지 - RSI 과매도 + MACD 골든 크로스'
        }
        
        # 주문 신호 알림 테스트
        trader._send_discord_order_notification(order_signal_data, "ORDER")
        print("✅ 주문 신호 알림 전송 완료")
        
        print("\n2. 주문 성공 결과 Discord 알림 테스트")
        print("-" * 30)
        
        # 주문 성공 결과 테스트 데이터
        success_result_data = order_signal_data.copy()
        success_result_data.update({
            'success': True,
            'uuid': 'test-uuid-12345',
            'error': ''
        })
        
        # 주문 성공 결과 알림 테스트
        trader._send_discord_order_notification(success_result_data, "RESULT")
        print("✅ 주문 성공 결과 알림 전송 완료")
        
        print("\n3. 주문 실패 결과 Discord 알림 테스트")
        print("-" * 30)
        
        # 주문 실패 결과 테스트 데이터
        failure_result_data = order_signal_data.copy()
        failure_result_data.update({
            'action': 'SELL',
            'success': False,
            'uuid': 'Failed',
            'error': '잔고 부족: 현재 KRW 잔고가 최소 주문 금액보다 적습니다.'
        })
        
        # 주문 실패 결과 알림 테스트
        trader._send_discord_order_notification(failure_result_data, "RESULT")
        print("✅ 주문 실패 결과 알림 전송 완료")
        
        print("\n" + "=" * 50)
        print("Discord 알림 테스트 완료!")
        print("Discord 채널에서 3개의 테스트 메시지를 확인하세요:")
        print("1. 🟢 BUY 주문 신호")
        print("2. ✅ BUY 주문 성공")
        print("3. ❌ SELL 주문 실패")
        print("=" * 50)
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_discord_notifications()
