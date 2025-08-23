#!/usr/bin/env python3
"""
Live_Crypto_Trader 클래스 테스트 스크립트
"""

import sys
import os
import threading
import time
import logging

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_crypto_trader():
    """Live_Crypto_Trader 테스트"""
    print("Live_Crypto_Trader 테스트 시작...")
    
    try:
        # trader 모듈 임포트 테스트
        print("1. trader 모듈 임포트...")
        from core import trader
        print("   ✓ trader 모듈 임포트 성공")
        
        # Live_Crypto_Trader 클래스 초기화 테스트
        print("2. Live_Crypto_Trader 초기화...")
        crypto_trader = trader.Live_Crypto_Trader(
            markets=['KRW-BTC'],  # 테스트용으로 BTC만 사용
            interval='1m',
            num_steps=5,
            min_confidence=0.7,
            trading_amount=10000
        )
        print("   ✓ Live_Crypto_Trader 초기화 성공")
        
        # 상태 확인 테스트
        print("3. 트레이더 상태 확인...")
        status = crypto_trader.get_status()
        print(f"   ✓ 상태 조회 성공: {status}")
        
        # 짧은 시간 동안 실행 테스트
        print("4. 짧은 시간 실행 테스트 (5초)...")
        
        # 종료 이벤트 생성
        shutdown_event = threading.Event()
        crypto_trader.set_shutdown_event(shutdown_event)
        
        # 트레이더를 별도 스레드에서 실행
        trader_thread = threading.Thread(target=crypto_trader.run)
        trader_thread.daemon = True
        trader_thread.start()
        
        # 5초 대기
        time.sleep(5)
        
        # 트레이더 중지
        print("5. 트레이더 중지...")
        crypto_trader.stop()
        shutdown_event.set()
        
        # 스레드 종료 대기
        trader_thread.join(timeout=5)
        
        if trader_thread.is_alive():
            print("   ⚠ 트레이더 스레드가 완전히 종료되지 않았습니다.")
        else:
            print("   ✓ 트레이더 중지 성공")
        
        print("\n✅ 모든 테스트 통과!")
        return True
        
    except ImportError as e:
        print(f"   ❌ 모듈 임포트 실패: {e}")
        return False
    except Exception as e:
        print(f"   ❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_main_integration():
    """main.py와의 통합 테스트"""
    print("\nmain.py 통합 테스트 시작...")
    
    try:
        # main.py에서 사용되는 트레이더 팩토리 함수 테스트
        print("1. 트레이더 팩토리 함수 테스트...")
        
        from core import trader
        
        # main.py에서 사용하는 람다 함수와 동일한 방식으로 테스트
        trader_factory = lambda: trader.Live_Crypto_Trader(
            markets=['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-ADA'],
            interval='1m',
            num_steps=5,
            min_confidence=0.7,
            trading_amount=10000
        )
        
        trader_instance = trader_factory()
        print("   ✓ 트레이더 팩토리 함수 성공")
        
        # 상태 확인
        status = trader_instance.get_status()
        print(f"   ✓ 상태 조회 성공: markets={status.get('markets', [])}")
        
        print("\n✅ main.py 통합 테스트 통과!")
        return True
        
    except Exception as e:
        print(f"   ❌ 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 함수"""
    setup_logging()
    
    print("=" * 60)
    print("Live_Crypto_Trader 테스트 스위트")
    print("=" * 60)
    
    # 개별 테스트
    test1_passed = test_crypto_trader()
    
    # 통합 테스트
    test2_passed = test_main_integration()
    
    print("\n" + "=" * 60)
    print("테스트 결과 요약:")
    print(f"  - Live_Crypto_Trader 기본 테스트: {'✅ 통과' if test1_passed else '❌ 실패'}")
    print(f"  - main.py 통합 테스트: {'✅ 통과' if test2_passed else '❌ 실패'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 모든 테스트가 성공했습니다!")
        return 0
    else:
        print("\n⚠️  일부 테스트가 실패했습니다.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
