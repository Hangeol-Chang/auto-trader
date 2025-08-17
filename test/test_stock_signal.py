#!/usr/bin/env python3
"""
주식 신호 처리 API 테스트 스크립트

사용법:
python test/test_stock_signal.py
또는 test 폴더에서: python test_stock_signal.py
"""

import requests
import json
import time

# 서버 URL 설정
SERVER_URL = "http://localhost:5000"

def test_stock_buy_signal(stock_code="005930", price=65000, quantity=1):
    """주식 매수 신호 테스트"""
    url = f"{SERVER_URL}/api/trading/stock-signal"
    
    payload = {
        "stock_code": stock_code,
        "action": "buy",
        "price": price,
        "quantity": quantity,
        "strategy": "Test Stock Strategy"
    }
    
    print(f"\n=== 주식 매수 신호 테스트 ({stock_code}) ===")
    print("전송 데이터:", json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"응답 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def test_stock_sell_signal(stock_code="005930", price=66000, quantity=1):
    """주식 매도 신호 테스트"""
    url = f"{SERVER_URL}/api/trading/stock-signal"
    
    payload = {
        "stock_code": stock_code,
        "action": "sell",
        "price": price,
        "quantity": quantity,
        "strategy": "Test Stock Strategy"
    }
    
    print(f"\n=== 주식 매도 신호 테스트 ({stock_code}) ===")
    print("전송 데이터:", json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"응답 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def test_market_order(stock_code="005930", action="buy", quantity=1):
    """시장가 주문 테스트"""
    url = f"{SERVER_URL}/api/trading/stock-signal"
    
    payload = {
        "stock_code": stock_code,
        "action": action,
        "quantity": quantity,
        "strategy": "Market Order Test"
    }
    
    print(f"\n=== 시장가 {action.upper()} 테스트 ({stock_code}) ===")
    print("전송 데이터:", json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"응답 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def test_stock_balance():
    """주식 잔고 조회 테스트"""
    url = f"{SERVER_URL}/api/trading/stock-balance"
    
    print(f"\n=== 주식 잔고 조회 테스트 ===")
    
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

def test_stock_price(stock_code="005930"):
    """주식 현재가 조회 테스트"""
    url = f"{SERVER_URL}/api/trading/stock-price/{stock_code}"
    
    print(f"\n=== 주식 현재가 조회 테스트 ({stock_code}) ===")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"응답 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("주가 정보:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def test_server_health():
    """서버 상태 확인"""
    url = f"{SERVER_URL}/api/trading/health"
    
    print(f"\n=== Trading API 서버 상태 확인 ===")
    
    try:
        response = requests.get(url, timeout=5)
        print(f"응답 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print("주식 신호 처리 API 테스트를 시작합니다...")
    
    # 서버 상태 확인
    if not test_server_health():
        print("❌ 서버가 응답하지 않습니다. 서버를 먼저 시작해주세요.")
        return
    
    print("✅ 서버가 정상적으로 응답합니다.")
    
    # 각종 테스트 실행
    tests = [
        ("주식 현재가 조회", lambda: test_stock_price("005930")),
        ("주식 잔고 조회", test_stock_balance),
        ("시장가 매수 주문", lambda: test_market_order("005930", "buy", 1)),
        ("지정가 매수 주문", lambda: test_stock_buy_signal("005930", 65000, 1)),
        ("지정가 매도 주문", lambda: test_stock_sell_signal("005930", 66000, 1)),
        ("시장가 매도 주문", lambda: test_market_order("005930", "sell", 1)),
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

if __name__ == "__main__":
    main()
