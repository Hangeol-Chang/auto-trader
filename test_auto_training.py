"""자동 모델 학습 기능 테스트"""

import sys
import os
import logging

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.trader import Live_Crypto_Trader

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_auto_training():
    """자동 학습 기능 테스트"""
    print("=" * 60)
    print("자동 모델 학습 기능 테스트")
    print("=" * 60)
    
    # 기존 모델 파일이 있는지 확인
    model_dir = "model/crypto_rl_models"
    
    print(f"\n1. 모델 디렉토리 확인: {model_dir}")
    if os.path.exists(model_dir):
        import glob
        existing_models = glob.glob(os.path.join(model_dir, "value_network_KRW_ETH_*.weights.h5"))
        print(f"   기존 KRW-ETH 모델 개수: {len(existing_models)}")
        for model in existing_models:
            print(f"   - {model}")
    else:
        print(f"   모델 디렉토리가 존재하지 않음")
    
    print(f"\n2. Live_Crypto_Trader 초기화 (테스트용 코인: KRW-ETH)")
    print("   ⚠️  주의: KRW-ETH 모델이 없으면 자동 학습이 시작됩니다!")
    print("   학습에는 시간이 걸릴 수 있습니다...")
    
    try:
        # KRW-ETH 코인으로 테스트 (모델이 없을 가능성이 높음)
        trader = Live_Crypto_Trader(
            markets=['KRW-ETH'],  # 테스트용 단일 코인
            interval='1m',
            num_steps=5,
            min_confidence=0.7,
            trading_amount=10000
        )
        
        print(f"\n3. 초기화 완료!")
        print(f"   로드된 모델 개수: {len(trader.models)}")
        
        for market, model in trader.models.items():
            if model:
                print(f"   ✅ [{market}] 모델 로드 성공")
            else:
                print(f"   ❌ [{market}] 모델 로드 실패")
        
        # 새로 생성된 모델 파일 확인
        if os.path.exists(model_dir):
            new_models = glob.glob(os.path.join(model_dir, "value_network_KRW_ETH_*.weights.h5"))
            print(f"\n4. 생성된 KRW-ETH 모델 개수: {len(new_models)}")
            for model in new_models:
                print(f"   - {model}")
        
        print(f"\n✅ 테스트 완료!")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auto_training()
