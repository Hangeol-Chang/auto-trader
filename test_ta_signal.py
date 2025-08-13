#!/usr/bin/env python3
"""
TradingView ta-signal 엔드포인트 테스트 스크립트

사용법:
python test_ta_signal.py
"""

import requests
import json
import time

# 서버 URL 설정
SERVER_URL = "http://localhost:5000"

def test_buy_signal(ticker="BTC"):
    """매수 신호 테스트"""
    url = f"{SERVER_URL}/ta-signal"
    
    payload = {
        "strategy": {
            "name": "Test Strategy",
            "settings": {
                "source": "[B]",
                "parameters": "20, 20, 1.5, 14, 5, 2"
            }
        },
        "instrument": {
            "ticker": ticker
        },
        "order": {
            "action": "buy",
            "quantity": "1"
        },
        "position": {
            "new_size": "1"
        }
    }
    
    print(f"\n=== 매수 신호 테스트 ({ticker}) ===")
    print("전송 데이터:", json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"응답 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def test_sell_signal(ticker="BTC"):
    """매도 신호 테스트"""
    url = f"{SERVER_URL}/ta-signal"
    
    payload = {
        "strategy": {
            "name": "Test Strategy",
            "settings": {
                "source": "[S]",
                "parameters": "20, 20, 1.5, 14, 5, 2"
            }
        },
        "instrument": {
            "ticker": ticker
        },
        "order": {
            "action": "sell",
            "quantity": "1"
        },
        "position": {
            "new_size": "0"
        }
    }
    
    print(f"\n=== 매도 신호 테스트 ({ticker}) ===")
    print("전송 데이터:", json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"응답 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def test_text_signal():
    """텍스트 형태 신호 테스트"""
    url = f"{SERVER_URL}/ta-signal"
    
    text_data = "BTC BUY SIGNAL - Test from script"
    
    print(f"\n=== 텍스트 신호 테스트 ===")
    print("전송 데이터:", text_data)
    
    try:
        response = requests.post(url, data=text_data, 
                               headers={'Content-Type': 'text/plain'}, timeout=10)
        print(f"응답 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def test_server_health():
    """서버 상태 확인"""
    url = f"{SERVER_URL}/health"
    
    print("\n=== 서버 상태 확인 ===")
    
    try:
        response = requests.get(url, timeout=5)
        print(f"응답 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"서버 연결 실패: {e}")
        print("서버가 실행 중인지 확인하세요.")
        return False

def test_balance():
    """잔고 조회 테스트"""
    url = f"{SERVER_URL}/test-balance"
    
    print("\n=== 잔고 조회 테스트 ===")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"응답 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"요청 실패: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print("TradingView ta-signal 엔드포인트 테스트")
    print("="*50)
    
    # 1. 서버 상태 확인
    if not test_server_health():
        print("\n❌ 서버에 연결할 수 없습니다. 먼저 서버를 실행하세요:")
        print("python main.py")
        return
    
    print("\n✅ 서버가 정상적으로 실행 중입니다.")
    
    # 2. 잔고 조회 테스트
    print("\n" + "="*50)
    test_balance()
    
    # 3. 매수 신호 테스트
    print("\n" + "="*50)
    test_buy_signal("BTC")
    
    time.sleep(2)  # 잠시 대기
    
    # 4. 매도 신호 테스트
    print("\n" + "="*50)
    test_sell_signal("BTC")
    
    time.sleep(2)  # 잠시 대기
    
    # 5. 다른 코인으로 테스트
    print("\n" + "="*50)
    test_buy_signal("ETH")
    
    # 6. 텍스트 신호 테스트
    print("\n" + "="*50)
    test_text_signal()
    
    print("\n" + "="*50)
    print("테스트 완료!")
    print("\n로그 확인:")
    print("- 서버 로그: logs/server_YYYYMMDD.log")
    print("- 신호 로그: data/ta-signal.txt")

if __name__ == "__main__":
    main()
