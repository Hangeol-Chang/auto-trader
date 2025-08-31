"""
실시간 코인 트레이딩 시스템 테스트

시스템의 주요 구성 요소들이 올바르게 작동하는지 테스트
"""

import sys
import os
import json
import time
from datetime import datetime

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(__file__))

def test_upbit_api():
    """업비트 API 연결 테스트"""
    print("\n=== 업비트 API 테스트 ===")
    
    try:
        from module.upbit_api import UpbitAPI
        
        api = UpbitAPI()
        
        # API 키 로드 테스트
        if api.access_key and api.secret_key:
            print("✅ API 키 로드 성공")
        else:
            print("❌ API 키 로드 실패")
            return False
        
        # 마켓 정보 테스트
        if api.market_info_cache:
            print(f"✅ 마켓 정보 로드 성공: {len(api.market_info_cache)}개")
        else:
            print("❌ 마켓 정보 로드 실패")
            return False
        
        # 잔고 조회 테스트
        balances = api.get_balances()
        if balances:
            print("✅ 잔고 조회 성공")
            krw_balance = next((b for b in balances if b['currency'] == 'KRW'), None)
            if krw_balance:
                print(f"   KRW 잔고: {float(krw_balance['balance']):,.0f}원")
        else:
            print("❌ 잔고 조회 실패")
            return False
        
        # 현재가 조회 테스트
        price = api.get_current_price('KRW-BTC')
        if price:
            print(f"✅ 현재가 조회 성공: BTC {price:,}원")
        else:
            print("❌ 현재가 조회 실패")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 업비트 API 테스트 실패: {e}")
        return False


def test_hybrid_model():
    """하이브리드 모델 로드 테스트"""
    print("\n=== 하이브리드 모델 테스트 ===")
    
    try:
        from model.crypto_rl_learner import CryptoReinforcementLearner
        
        # 모델 파일 존재 확인
        model_dir = "model/crypto_rl_models"
        if not os.path.exists(model_dir):
            print("❌ 모델 디렉토리 없음")
            return False
        
        import glob
        model_files = glob.glob(os.path.join(model_dir, "value_network_KRW_BTC_*.weights.h5"))
        
        if not model_files:
            print("❌ BTC 모델 파일 없음")
            print("   다음 명령으로 모델을 학습하세요:")
            print("   python model/train_crypto_rl_hybrid.py --market KRW-BTC --epochs 100")
            return False
        
        print(f"✅ 모델 파일 발견: {len(model_files)}개")
        
        # 모델 로드 테스트
        learner = CryptoReinforcementLearner(
            market='KRW-BTC',
            net='dnn_lstm',
            num_steps=5,
            reuse_models=True
        )
        
        if learner.value_network:
            print("✅ 하이브리드 모델 생성 성공")
            
            # 가중치 로드 테스트
            latest_model = max(model_files, key=os.path.getmtime)
            learner.value_network.load_weights(latest_model)
            print(f"✅ 모델 가중치 로드 성공: {os.path.basename(latest_model)}")
            
            return True
        else:
            print("❌ 모델 생성 실패")
            return False
        
    except Exception as e:
        print(f"❌ 하이브리드 모델 테스트 실패: {e}")
        return False


def test_data_processing():
    """데이터 처리 테스트"""
    print("\n=== 데이터 처리 테스트 ===")
    
    try:
        from module.crypto.crypto_data_manager import get_candle_data
        from datetime import datetime, timedelta
        
        # 현재 시간과 1시간 전 시간 계산
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        end_datetime = end_time.strftime('%Y%m%d%H%M')
        start_datetime = start_time.strftime('%Y%m%d%H%M')
        
        # 캔들 데이터 조회
        df = get_candle_data(
            market='KRW-BTC', 
            interval='1m',
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            use_cache=True
        )
        
        if df is not None and len(df) > 0:
            print(f"✅ 캔들 데이터 조회 성공: {len(df)}개")
            print(f"   최신 가격: {df.iloc[-1]['trade_price']:,}원")
            print(f"   시간 범위: {df.iloc[0]['candle_date_time_kst']} ~ {df.iloc[-1]['candle_date_time_kst']}")
            return True
        else:
            print("❌ 캔들 데이터 조회 실패")
            return False
        
    except Exception as e:
        print(f"❌ 데이터 처리 테스트 실패: {e}")
        return False


def test_orderer():
    """주문 시스템 테스트"""
    print("\n=== 주문 시스템 테스트 ===")
    
    try:
        from module.crypto.crypto_orderer import Live_Orderer
        
        orderer = Live_Orderer()
        print("✅ 주문 시스템 초기화 성공")
        
        # 잔고 정보 테스트
        balance_info = orderer.get_balance_info()
        if balance_info and 'balances' in balance_info:
            print("✅ 잔고 정보 조회 성공")
            total_krw = balance_info.get('total_krw', 0)
            print(f"   총 자산: {total_krw:,.0f}원")
        else:
            print("❌ 잔고 정보 조회 실패")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 주문 시스템 테스트 실패: {e}")
        return False


def test_websocket():
    """웹소켓 연결 테스트"""
    print("\n=== 웹소켓 연결 테스트 ===")
    
    try:
        import websocket
        import json
        import threading
        import time
        
        connected = False
        data_received = False
        
        def on_message(ws, message):
            nonlocal data_received
            data_received = True
            print("✅ 웹소켓 데이터 수신 성공")
            ws.close()
        
        def on_open(ws):
            nonlocal connected
            connected = True
            print("✅ 웹소켓 연결 성공")
            
            # 구독 메시지 전송
            subscribe_msg = [
                {"ticket": "test"},
                {
                    "type": "ticker",
                    "codes": ["KRW-BTC"]
                }
            ]
            ws.send(json.dumps(subscribe_msg))
        
        def on_error(ws, error):
            print(f"❌ 웹소켓 에러: {error}")
        
        # 웹소켓 연결 테스트
        ws = websocket.WebSocketApp(
            "wss://api.upbit.com/websocket/v1",
            on_open=on_open,
            on_message=on_message,
            on_error=on_error
        )
        
        # 별도 스레드에서 실행
        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        # 5초 대기
        for i in range(50):
            time.sleep(0.1)
            if data_received:
                break
        
        if connected and data_received:
            print("✅ 웹소켓 테스트 완료")
            return True
        else:
            print("❌ 웹소켓 테스트 실패")
            return False
        
    except Exception as e:
        print(f"❌ 웹소켓 테스트 실패: {e}")
        return False


def test_trader_creation():
    """트레이더 생성 테스트"""
    print("\n=== 트레이더 생성 테스트 ===")
    
    try:
        from core.trader import Live_Crypto_Trader
        
        # 트레이더 인스턴스 생성
        trader = Live_Crypto_Trader(
            markets=['KRW-BTC'],
            interval='1m',
            num_steps=5,
            min_confidence=0.7,
            trading_amount=5000
        )
        
        print("✅ 트레이더 인스턴스 생성 성공")
        
        # 설정 확인
        print(f"   거래 마켓: {trader.markets}")
        print(f"   최소 신뢰도: {trader.min_confidence}")
        print(f"   거래 금액: {trader.trading_amount:,}원")
        
        # 상태 정보 확인
        status = trader.get_status()
        if status:
            print("✅ 트레이더 상태 조회 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ 트레이더 생성 테스트 실패: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("🚀 실시간 코인 트레이딩 시스템 테스트 시작")
    print("=" * 50)
    
    tests = [
        ("업비트 API", test_upbit_api),
        ("데이터 처리", test_data_processing),
        ("주문 시스템", test_orderer),
        ("웹소켓 연결", test_websocket),
        ("하이브리드 모델", test_hybrid_model),
        ("트레이더 생성", test_trader_creation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 예외 발생: {e}")
            results.append((test_name, False))
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{test_name:15} : {status}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"전체 테스트: {passed}/{total} 성공 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 모든 테스트 통과! 시스템이 정상적으로 설정되었습니다.")
        print("\n다음 명령으로 실시간 트레이딩을 시작하세요:")
        print("python main.py")
        print("\n대시보드: http://localhost:5000/dashboard")
    else:
        print("⚠️  일부 테스트 실패. 위의 오류 메시지를 확인하세요.")
        
        if not any(name == "하이브리드 모델" and result for name, result in results):
            print("\n💡 하이브리드 모델이 없으면 다음 명령으로 학습하세요:")
            print("python model/train_crypto_rl_hybrid.py --market KRW-BTC --epochs 100")


if __name__ == "__main__":
    main()
