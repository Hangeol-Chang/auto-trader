"""
Simple Crypto RL Test

간단한 crypto 강화학습 테스트
"""

import os
import sys
import numpy as np

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from model.crypto_rl_learner import CryptoReinforcementLearner


def simple_test():
    """가장 간단한 테스트"""
    print("=== Simple Crypto RL Test ===")
    
    try:
        # 가장 기본적인 설정으로 학습자 생성
        learner = CryptoReinforcementLearner(
            market='KRW-BTC',
            interval='1d',
            balance=1000000,
            num_epochs=3,  # 매우 짧은 테스트
            min_trading_price=50000,
            max_trading_price=200000,
            net='dnn',
            lr=0.01,
            start_epsilon=0.9
        )
        
        print(f"✓ Data loaded successfully")
        print(f"  - Chart data: {learner.chart_data.shape}")
        print(f"  - Training data: {learner.training_data.shape}")
        print(f"  - Features: {learner.num_features}")
        
        # 단일 샘플 테스트
        print("\n=== Testing sample building ===")
        learner.reset()
        sample = learner.build_sample()
        print(f"✓ Sample built: shape={np.array(sample).shape}, type={type(sample)}")
        
        # 신경망 초기화 테스트
        print("\n=== Testing network initialization ===")
        learner.init_value_network()
        print(f"✓ Value network initialized")
        
        # 단일 예측 테스트
        print("\n=== Testing prediction ===")
        pred = learner.value_network.predict(sample)
        print(f"✓ Prediction successful: {pred}")
        
        # 에이전트 행동 테스트
        print("\n=== Testing agent actions ===")
        action, confidence, exploration = learner.agent.decide_action(pred, None, 0.5)
        print(f"✓ Action decided: action={action}, confidence={confidence}, exploration={exploration}")
        
        # 행동 수행 테스트
        reward = learner.agent.act(action, confidence)
        print(f"✓ Action executed: reward={reward}")
        
        print("\n=== All basic tests passed! ===")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def mini_training_test():
    """매우 짧은 학습 테스트"""
    print("\n=== Mini Training Test ===")
    
    try:
        learner = CryptoReinforcementLearner(
            market='KRW-BTC',
            interval='1d',
            balance=1000000,
            num_epochs=2,
            min_trading_price=50000,
            max_trading_price=200000,
            net='dnn',
            lr=0.01
        )
        
        print("Starting mini training...")
        epoch_summary = learner.fit(
            num_epoches=2,
            balance=1000000,
            learning=True,
            start_epsilon=0.8
        )
        
        print(f"✓ Mini training completed!")
        final_result = epoch_summary[-1]
        print(f"  - Final P&L: {final_result['profitloss']:6.4f}")
        print(f"  - Actions: Buy={final_result['num_buy']}, Sell={final_result['num_sell']}, Hold={final_result['num_hold']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Mini training failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 단계별 테스트 실행
    success = True
    
    # 1. 기본 기능 테스트
    if not simple_test():
        success = False
        print("\n기본 테스트 실패. 미니 학습 테스트는 건너뜁니다.")
    else:
        # 2. 미니 학습 테스트
        if not mini_training_test():
            success = False
    
    print("\n" + "="*50)
    if success:
        print("🎉 모든 테스트 성공!")
    else:
        print("❌ 일부 테스트 실패")
