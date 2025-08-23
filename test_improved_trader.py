#!/usr/bin/env python3
"""
수정된 Live_Crypto_Trader 테스트 스크립트
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

def test_improved_crypto_trader():
    """개선된 Live_Crypto_Trader 테스트"""
    print("개선된 Live_Crypto_Trader 테스트 시작...")
    
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
            min_confidence=0.5,  # 낮춰서 테스트하기 쉽게
            trading_amount=5000   # 소액으로 테스트
        )
        print("   ✓ Live_Crypto_Trader 초기화 성공")
        
        # 상태 확인 테스트
        print("3. 트레이더 상태 확인...")
        status = crypto_trader.get_status()
        print(f"   ✓ 상태 조회 성공")
        print(f"   - 모델 로드 수: {len(status.get('models_loaded', []))}")
        print(f"   - 데이터 상태: {status.get('data_status', {})}")
        
        # 기술적 분석 테스트
        print("4. 기본 기술적 분석 테스트...")
        if 'KRW-BTC' in status.get('data_status', {}):
            analysis_result = crypto_trader._basic_technical_analysis('KRW-BTC')
            print(f"   ✓ 기술적 분석 결과: {analysis_result}")
        else:
            print("   ⚠ 데이터 부족으로 기술적 분석 스킵")
        
        # 5초간 실시간 테스트
        print("5. 5초간 실시간 테스트...")
        
        # 종료 이벤트 생성
        shutdown_event = threading.Event()
        crypto_trader.set_shutdown_event(shutdown_event)
        
        # 트레이더를 별도 스레드에서 실행
        trader_thread = threading.Thread(target=crypto_trader.run)
        trader_thread.daemon = True
        trader_thread.start()
        
        # 5초 대기
        start_time = time.time()
        while time.time() - start_time < 5:
            time.sleep(1)
            print(f"   실행 중... {int(time.time() - start_time)}초")
        
        # 트레이더 중지
        print("6. 트레이더 중지...")
        crypto_trader.stop()
        shutdown_event.set()
        
        # 스레드 종료 대기
        trader_thread.join(timeout=5)
        
        if trader_thread.is_alive():
            print("   ⚠ 트레이더 스레드가 완전히 종료되지 않았습니다.")
        else:
            print("   ✓ 트레이더 중지 성공")
        
        print("\n✅ 개선된 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"   ❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 함수"""
    setup_logging()
    
    print("=" * 60)
    print("개선된 Live_Crypto_Trader 테스트")
    print("=" * 60)
    
    # 개선된 테스트
    test_passed = test_improved_crypto_trader()
    
    print("\n" + "=" * 60)
    print("테스트 결과:")
    print(f"  - 개선된 Live_Crypto_Trader: {'✅ 통과' if test_passed else '❌ 실패'}")
    
    if test_passed:
        print("\n🎉 테스트가 성공했습니다!")
        return 0
    else:
        print("\n⚠️  테스트가 실패했습니다.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
