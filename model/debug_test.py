"""
Debug Crypto RL Test

crypto 강화학습 디버그 테스트 - 단계별로 확인
"""

import os
import sys
import numpy as np

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from model.crypto_rl_learner import CryptoReinforcementLearner


def debug_data_loading():
    """데이터 로딩 테스트"""
    print("=== 데이터 로딩 테스트 ===")
    
    try:
        learner = CryptoReinforcementLearner(
            market='KRW-BTC',
            interval='1d',
            balance=1000000,
            num_epochs=1,
            min_trading_price=50000,
            max_trading_price=200000
        )
        
        print(f"✓ 데이터 로딩 성공")
        print(f"  차트 데이터: {learner.chart_data.shape}")
        print(f"  학습 데이터: {learner.training_data.shape}")
        print(f"  특성 수: {learner.num_features}")
        
        # 데이터 샘플 확인
        print(f"\n차트 데이터 샘플:")
        print(learner.chart_data.head())
        
        print(f"\n학습 데이터 샘플:")
        print(learner.training_data.head())
        
        return learner
        
    except Exception as e:
        print(f"✗ 데이터 로딩 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def debug_environment_step(learner):
    """환경 스텝 테스트"""
    print("\n=== 환경 스텝 테스트 ===")
    
    try:
        learner.reset()
        
        print("환경 단계별 테스트:")
        for i in range(5):  # 처음 5스텝만 테스트
            sample = learner.build_sample()
            if sample is None:
                print(f"  스텝 {i}: 샘플 없음 (종료)")
                break
            
            print(f"  스텝 {i}: 샘플 크기={len(sample)}, 환경 idx={learner.environment.idx}")
            
            # 가격 확인
            price = learner.environment.get_price()
            print(f"    현재 가격: {price}")
            
        return True
        
    except Exception as e:
        print(f"✗ 환경 스텝 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def debug_agent_actions(learner):
    """에이전트 행동 테스트"""
    print("\n=== 에이전트 행동 테스트 ===")
    
    try:
        learner.reset()
        
        # 첫 번째 샘플 생성
        sample = learner.build_sample()
        if sample is None:
            print("✗ 샘플 생성 실패")
            return False
        
        print(f"✓ 샘플 생성: {len(sample)} 특성")
        
        # 에이전트 상태 확인
        status = learner.agent.get_status()
        print(f"✓ 에이전트 상태: {status}")
        
        # 랜덤 행동 테스트
        for action in range(3):  # BUY, SELL, HOLD
            print(f"\n행동 {action} 테스트:")
            
            # 행동 유효성 검사
            valid = learner.agent.validate_action(action)
            print(f"  유효성: {valid}")
            
            if valid:
                # 행동 수행
                reward = learner.agent.act(action, 0.5)
                print(f"  보상: {reward}")
                print(f"  포트폴리오: {learner.agent.portfolio_value}")
        
        return True
        
    except Exception as e:
        print(f"✗ 에이전트 행동 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def debug_single_epoch(learner):
    """단일 에포크 테스트"""
    print("\n=== 단일 에포크 테스트 ===")
    
    try:
        # 신경망 초기화
        learner.init_value_network()
        print("✓ 가치 신경망 초기화")
        
        # 에포크 시뮬레이션
        learner.reset()
        learner.agent.set_balance(1000000)
        
        step_count = 0
        max_steps = 10  # 처음 10스텝만
        
        print(f"단일 에포크 시뮬레이션 (최대 {max_steps} 스텝):")
        
        while step_count < max_steps:
            # 샘플 생성
            sample = learner.build_sample()
            if sample is None:
                print(f"  스텝 {step_count}: 데이터 종료")
                break
            
            # 예측
            pred_value = learner.value_network.predict(sample)
            
            # 행동 결정
            action, confidence, exploration = learner.agent.decide_action(
                pred_value, None, 0.5)
            
            # 행동 수행
            reward = learner.agent.act(action, confidence)
            
            print(f"  스텝 {step_count}: 행동={action}, 신뢰도={confidence:.3f}, "
                  f"탐험={exploration}, 보상={reward:.6f}")
            
            step_count += 1
        
        print(f"✓ 단일 에포크 완료: {step_count} 스텝")
        print(f"  최종 포트폴리오: {learner.agent.portfolio_value:,.0f}")
        print(f"  최종 손익: {learner.agent.profitloss:.6f}")
        
        return True
        
    except Exception as e:
        print(f"✗ 단일 에포크 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Crypto RL 디버그 테스트 시작\n")
    
    # 1. 데이터 로딩 테스트
    learner = debug_data_loading()
    if learner is None:
        print("데이터 로딩 실패로 테스트 중단")
        exit(1)
    
    # 2. 환경 스텝 테스트
    if not debug_environment_step(learner):
        print("환경 스텝 실패로 테스트 중단")
        exit(1)
    
    # 3. 에이전트 행동 테스트
    if not debug_agent_actions(learner):
        print("에이전트 행동 실패로 테스트 중단")
        exit(1)
    
    # 4. 단일 에포크 테스트
    if not debug_single_epoch(learner):
        print("단일 에포크 실패로 테스트 중단")
        exit(1)
    
    print("\n" + "="*50)
    print("🎉 모든 디버그 테스트 성공!")
    print("이제 실제 학습을 시도할 수 있습니다.")
