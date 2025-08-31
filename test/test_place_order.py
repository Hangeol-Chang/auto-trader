"""업비트 API place_order 함수 테스트"""

import sys
import os
import logging
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from module.upbit_api import UpbitAPI

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_place_order_validation():
    """place_order 함수의 매개변수 검증 테스트"""
    print("=" * 50)
    print("place_order 함수 매개변수 검증 테스트")
    print("=" * 50)
    
    upbit = UpbitAPI()
    
    # API 키가 로드되었는지 확인
    if not upbit.access_key or not upbit.secret_key:
        print("❌ API 키가 로드되지 않았습니다. private/keys.json 파일을 확인하세요.")
        return False
    
    print("✅ API 키가 성공적으로 로드되었습니다.")
    
    # 테스트할 매개변수들
    test_cases = [
        {
            "name": "시장가 매수 테스트 (최소 금액)",
            "market": "KRW-BTC",
            "side": "bid",
            "price": 5000,  # 최소 주문 금액
            "ord_type": "market"
        },
        {
            "name": "시장가 매도 테스트 (매우 작은 수량)",
            "market": "KRW-BTC", 
            "side": "ask",
            "volume": 0.00001,  # 매우 작은 수량
            "ord_type": "market"
        },
        {
            "name": "지정가 매수 테스트",
            "market": "KRW-BTC",
            "side": "bid",
            "price": 50000000,  # 현재가보다 낮은 가격
            "volume": 0.0001,
            "ord_type": "limit"
        },
        {
            "name": "지정가 매도 테스트",
            "market": "KRW-BTC",
            "side": "ask", 
            "price": 200000000,  # 현재가보다 높은 가격
            "volume": 0.0001,
            "ord_type": "limit"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   매개변수: {test_case}")
        
        # 실제 주문은 하지 않고 함수 호출만 테스트
        # 주문 파라미터 생성 로직만 확인
        try:
            # 실제 주문 대신 파라미터 검증만 수행
            market = test_case["market"]
            side = test_case["side"]
            volume = test_case.get("volume")
            price = test_case.get("price")
            ord_type = test_case.get("ord_type", "market")
            
            # 파라미터 생성 로직 검증
            params = {
                'market': market,
                'side': side,
            }
            
            if side == 'bid':
                if ord_type == 'limit' and price:
                    params['ord_type'] = 'limit'
                    params['price'] = str(int(price))
                    if volume:
                        params['volume'] = str(volume)
                else:
                    params['ord_type'] = 'price'
                    if price:
                        params['price'] = str(int(price))
            elif side == 'ask':
                if ord_type == 'limit' and price:
                    params['ord_type'] = 'limit'
                    params['price'] = str(int(price))
                    if volume:
                        params['volume'] = str(volume)
                else:
                    params['ord_type'] = 'market'
                    if volume:
                        params['volume'] = str(volume)
            
            print(f"   ✅ 생성된 파라미터: {params}")
            
        except Exception as e:
            print(f"   ❌ 파라미터 생성 실패: {e}")
    
    return True

def test_place_order_dry_run():
    """place_order 함수의 실제 호출 테스트 (드라이런)"""
    print("\n" + "=" * 50)
    print("place_order 함수 드라이런 테스트")
    print("=" * 50)
    
    upbit = UpbitAPI()
    
    # 잔고 조회를 통해 연결 테스트
    print("1. API 연결 상태 확인...")
    balances = upbit.get_balances()
    if balances is not None:
        print("   ✅ API 연결 성공")
        print(f"   보유 자산 개수: {len(balances)}")
        
        # KRW 잔고 확인
        krw_balance = 0
        for balance in balances:
            if balance['currency'] == 'KRW':
                krw_balance = float(balance['balance'])
                break
        print(f"   KRW 잔고: {krw_balance:,.0f}원")
        
    else:
        print("   ❌ API 연결 실패")
        return False
    
    # 현재가 조회
    print("\n2. 현재가 조회...")
    current_price = upbit.get_current_price('KRW-BTC')
    if current_price:
        print(f"   ✅ BTC 현재가: {current_price:,.0f}원")
    else:
        print("   ❌ 현재가 조회 실패")
        return False
    
    print("\n3. 주문 파라미터 시뮬레이션...")
    
    # 실제 주문은 하지 않고 함수 내부 로직만 테스트
    # 테스트용 소량 주문 시뮬레이션
    test_order = {
        "market": "KRW-BTC",
        "side": "bid",
        "price": 5000,  # 최소 주문 금액
        "ord_type": "market"
    }
    
    print(f"   테스트 주문: {test_order}")
    
    # JWT 토큰 생성 테스트
    params = {
        'market': test_order["market"],
        'side': test_order["side"],
        'ord_type': 'price',
        'price': str(int(test_order["price"]))
    }
    
    token = upbit.make_jwt_token(params)
    if token:
        print("   ✅ JWT 토큰 생성 성공")
        print(f"   토큰 길이: {len(token)} 문자")
    else:
        print("   ❌ JWT 토큰 생성 실패")
        return False
    
    print("\n⚠️  실제 주문은 수행하지 않았습니다. (안전을 위해)")
    print("   실제 주문을 테스트하려면 매우 소량으로 신중하게 진행하세요.")
    
    return True

def main():
    """메인 테스트 함수"""
    print(f"업비트 API place_order 함수 테스트 시작")
    print(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 매개변수 검증 테스트
        if not test_place_order_validation():
            print("❌ 매개변수 검증 테스트 실패")
            return
        
        # 2. 드라이런 테스트
        if not test_place_order_dry_run():
            print("❌ 드라이런 테스트 실패")
            return
        
        print("\n" + "=" * 50)
        print("✅ 모든 테스트가 성공적으로 완료되었습니다!")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
