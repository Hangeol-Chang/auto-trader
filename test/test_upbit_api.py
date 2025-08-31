#!/usr/bin/env python3
"""
업비트 API 직접 테스트
"""

import requests
import json
from datetime import datetime, timedelta

def test_upbit_api_direct():
    """업비트 API 직접 호출 테스트"""
    print("=== 업비트 API 직접 테스트 ===")
    
    # 업비트 1분봉 API 엔드포인트
    url = "https://api.upbit.com/v1/candles/minutes/1"
    
    # 파라미터 설정
    params = {
        'market': 'KRW-BTC',
        'count': 10  # 최근 10개 캔들
    }
    
    try:
        print(f"요청 URL: {url}")
        print(f"파라미터: {params}")
        
        response = requests.get(url, params=params)
        print(f"응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 성공! 데이터 개수: {len(data)}")
            print("최근 3개 캔들:")
            for i, candle in enumerate(data[:3]):
                print(f"  {i+1}. {candle}")
        else:
            print(f"❌ 실패: {response.text}")
            
    except Exception as e:
        print(f"❌ 오류: {e}")

def test_different_timeframes():
    """다른 시간 프레임 테스트"""
    print("\n=== 다른 시간 프레임 테스트 ===")
    
    timeframes = [
        ('1분봉', 'https://api.upbit.com/v1/candles/minutes/1'),
        ('5분봉', 'https://api.upbit.com/v1/candles/minutes/5'),
        ('1시간봉', 'https://api.upbit.com/v1/candles/minutes/60'),
        ('일봉', 'https://api.upbit.com/v1/candles/days')
    ]
    
    for name, url in timeframes:
        try:
            response = requests.get(url, params={'market': 'KRW-BTC', 'count': 5})
            if response.status_code == 200:
                data = response.json()
                print(f"✓ {name}: {len(data)}개 데이터")
            else:
                print(f"❌ {name}: 실패")
        except Exception as e:
            print(f"❌ {name}: 오류 - {e}")

def test_timestamp_format():
    """시간 범위 지정 테스트"""
    print("\n=== 시간 범위 지정 테스트 ===")
    
    # UTC 시간으로 시도
    now = datetime.utcnow()
    to_time = now.isoformat() + 'Z'
    
    url = "https://api.upbit.com/v1/candles/minutes/1"
    params = {
        'market': 'KRW-BTC',
        'to': to_time,
        'count': 10
    }
    
    try:
        print(f"UTC 시간 파라미터: {params}")
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ UTC 시간 기준 성공: {len(data)}개 데이터")
            if data:
                print(f"최신 캔들 시간: {data[0]['candle_date_time_utc']}")
        else:
            print(f"❌ UTC 시간 기준 실패: {response.text}")
            
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    test_upbit_api_direct()
    test_different_timeframes()
    test_timestamp_format()
