#!/usr/bin/env python3
"""
신규 TradingView Signal API 테스트 스크립트

사용법:
python test/test_ta_signal.py
또는 test 폴더에서: python test_ta_signal.py

레거시 ta-signal에서 신규 /api/tradingview/signal로 업데이트
"""

import requests
import json
import time
from datetime import datetime

# 서버 URL 설정
SERVER_URL = "http://localhost:5000"

def test_crypto_buy_signal(ticker="BTCKRW", price=95000000, quantity=0.001):
    """암호화폐 매수 신호 테스트 (신규 API)"""
    url = f"{SERVER_URL}/api/tradingview/signal"
    
    payload = {
        "ticker": ticker,
        "action": "buy",
        "price": price,
        "quantity": quantity,
        "strategy": "Test Buy Strategy",
        "timestamp": datetime.now().isoformat(),
        "exchange": "UPBIT"
    }
    
    print(f"\n=== 암호화폐 매수 신호 테스트 ({ticker}) ===")
    print("전송 데이터:", json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"응답 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def test_crypto_sell_signal(ticker="BTCKRW", price=94000000, quantity=0.001):
    """암호화폐 매도 신호 테스트 (신규 API)"""
    url = f"{SERVER_URL}/api/tradingview/signal"
    
    payload = {
        "ticker": ticker,
        "action": "sell",
        "price": price,
        "quantity": quantity,
        "strategy": "Test Sell Strategy",
        "timestamp": datetime.now().isoformat(),
        "exchange": "UPBIT"
    }
    
    print(f"\n=== 암호화폐 매도 신호 테스트 ({ticker}) ===")
    print("전송 데이터:", json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"응답 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def test_market_order(ticker="DOTKRW", action="buy", quantity=1):
    """시장가 주문 테스트 (가격 없음)"""
    url = f"{SERVER_URL}/api/tradingview/signal"
    
    payload = {
        "ticker": ticker,
        "action": action,
        "quantity": quantity,
        "strategy": "Market Order Test",
        "timestamp": datetime.now().isoformat(),
        "exchange": "UPBIT"
    }
    
    print(f"\n=== 시장가 {action.upper()} 테스트 ({ticker}) ===")
    print("전송 데이터:", json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"응답 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def test_signal_test_endpoint(ticker="BTCKRW"):
    """신호 테스트 엔드포인트 테스트"""
    url = f"{SERVER_URL}/api/tradingview/signal-test"
    
    payload = {
        "ticker": ticker,
        "action": "buy",
        "quantity": 0.001,
        "strategy": "Test Signal"
    }
    
    print(f"\n=== 신호 테스트 엔드포인트 ({ticker}) ===")
    print("전송 데이터:", json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"응답 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def test_balance():
    """잔고 조회 테스트"""
    url = f"{SERVER_URL}/api/trading/balance"
    
    print(f"\n=== 암호화폐 잔고 조회 테스트 ===")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"응답 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("잔고 정보:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def test_markets():
    """지원 마켓 조회 테스트"""
    url = f"{SERVER_URL}/api/trading/markets"
    
    print(f"\n=== 지원 마켓 조회 테스트 ===")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"응답 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("지원 마켓:")
            print(json.dumps(data[:5], indent=2, ensure_ascii=False))  # 처음 5개만 출력
            print(f"... 총 {len(data)}개 마켓")
        else:
            print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def test_health_checks():
    """상태 확인 테스트"""
    endpoints = [
        ("/api/tradingview/health", "TradingView API"),
        ("/api/trading/health", "Trading API")
    ]
    
    results = []
    for endpoint, name in endpoints:
        url = f"{SERVER_URL}{endpoint}"
        print(f"\n=== {name} 상태 확인 ===")
        
        try:
            response = requests.get(url, timeout=5)
            print(f"응답 코드: {response.status_code}")
            print(f"응답 내용: {response.text}")
            results.append((name, response.status_code == 200))
        except requests.exceptions.RequestException as e:
            print(f"요청 실패: {e}")
            results.append((name, False))
    
    return all(success for _, success in results)

def main():
    """메인 테스트 실행"""
    print("신규 TradingView Signal API 테스트를 시작합니다...")
    
    # 상태 확인
    if not test_health_checks():
        print("❌ 일부 API가 응답하지 않습니다. 서버를 먼저 시작해주세요.")
        return
    
    print("✅ API가 정상적으로 응답합니다.")
    
    # 각종 테스트 실행
    tests = [
        ("지원 마켓 조회", test_markets),
        ("암호화폐 잔고 조회", test_balance),
        ("신호 테스트 엔드포인트", lambda: test_signal_test_endpoint("BTCKRW")),
        ("BTC 지정가 매수", lambda: test_crypto_buy_signal("BTCKRW", 95000000, 0.001)),
        ("BTC 지정가 매도", lambda: test_crypto_sell_signal("BTCKRW", 94000000, 0.001)),
        ("ETH 지정가 매수", lambda: test_crypto_buy_signal("ETHKRW", 3500000, 0.01)),
        ("ETH 지정가 매도", lambda: test_crypto_sell_signal("ETHKRW", 3450000, 0.01)),
        ("DOT 시장가 매수", lambda: test_market_order("DOTKRW", "buy", 1)),
        ("DOT 시장가 매도", lambda: test_market_order("DOTKRW", "sell", 1)),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"테스트: {test_name}")
        success = test_func()
        results.append((test_name, success))
        time.sleep(1)  # API 호출 간격
    
    # 결과 요약
    print(f"\n{'='*50}")
    print("테스트 결과 요약:")
    for test_name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"  {test_name}: {status}")
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    print(f"\n전체: {success_count}/{total_count} 성공")
    
    print(f"\n{'='*50}")
    print("API 마이그레이션 정보:")
    print("- 레거시: /ta-signal")
    print("- 신규: /api/tradingview/signal")
    print("- 주요 변경사항:")
    print("  * 간소화된 페이로드 구조")
    print("  * 직접적인 ticker/action/price/quantity 필드")
    print("  * timestamp 및 exchange 필드 추가")
    print("  * 중첩된 객체 구조 제거")
    print("  * 향상된 에러 처리")

if __name__ == "__main__":
    main()
