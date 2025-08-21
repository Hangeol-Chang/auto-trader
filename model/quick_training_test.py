"""
Quick Training Test

빠른 crypto 강화학습 테스트 - 실제 학습 확인
"""

import os
import sys

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from model.crypto_rl_learner import CryptoReinforcementLearner


def quick_training_test():
    """빠른 학습 테스트"""
    print("=== 빠른 Crypto RL 학습 테스트 ===")
    
    try:
        # 매우 짧은 학습 설정
        learner = CryptoReinforcementLearner(
            market='KRW-BTC',
            interval='1d',
            balance=1000000,
            num_epochs=3,        # 3 에포크만
            min_trading_price=50000,
            max_trading_price=200000,
            net='dnn',
            lr=0.01,             # 높은 학습률로 빠른 학습
            start_epsilon=0.8
        )
        
        print(f"설정 완료:")
        print(f"  마켓: {learner.market}")
        print(f"  데이터: {len(learner.chart_data)} 캔들")
        print(f"  특성: {learner.num_features}")
        
        # 학습 실행
        print(f"\n학습 시작 (3 에포크)...")
        epoch_summary = learner.fit(
            num_epoches=3,
            balance=1000000,
            learning=True,
            start_epsilon=0.8
        )
        
        # 결과 분석
        print(f"\n=== 학습 결과 ===")
        for i, epoch in enumerate(epoch_summary):
            print(f"에포크 {i}: "
                  f"스텝={epoch['steps']}, "
                  f"포트폴리오={epoch['portfolio_value']:,.0f}, "
                  f"손익={epoch['profitloss']:6.4f}, "
                  f"행동(B/S/H)={epoch['num_buy']}/{epoch['num_sell']}/{epoch['num_hold']}")
        
        final_result = epoch_summary[-1]
        print(f"\n최종 결과:")
        print(f"  초기 잔고: 1,000,000")
        print(f"  최종 포트폴리오: {final_result['portfolio_value']:,.0f}")
        print(f"  총 손익: {final_result['profitloss']:6.4f} ({final_result['profitloss']*100:6.2f}%)")
        print(f"  총 행동: 매수={final_result['num_buy']}, 매도={final_result['num_sell']}, 관망={final_result['num_hold']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 학습 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def medium_training_test():
    """중간 길이 학습 테스트"""
    print("\n=== 중간 길이 Crypto RL 학습 테스트 ===")
    
    try:
        learner = CryptoReinforcementLearner(
            market='KRW-BTC',
            interval='1d',
            balance=5000000,     # 500만원
            num_epochs=20,       # 20 에포크
            min_trading_price=100000,
            max_trading_price=1000000,
            net='dnn',
            lr=0.005,
            start_epsilon=0.9
        )
        
        print(f"중간 학습 시작 (20 에포크)...")
        epoch_summary = learner.fit(
            num_epoches=20,
            balance=5000000,
            learning=True,
            start_epsilon=0.9
        )
        
        # 최종 결과만 출력
        final_result = epoch_summary[-1]
        print(f"\n중간 학습 완료!")
        print(f"  초기 잔고: 5,000,000")
        print(f"  최종 포트폴리오: {final_result['portfolio_value']:,.0f}")
        print(f"  총 손익: {final_result['profitloss']:6.4f} ({final_result['profitloss']*100:6.2f}%)")
        
        # 학습 진행 분석
        profits = [epoch['profitloss'] for epoch in epoch_summary]
        print(f"  최고 수익: {max(profits):6.4f} ({max(profits)*100:6.2f}%)")
        print(f"  최저 수익: {min(profits):6.4f} ({min(profits)*100:6.2f}%)")
        
        return True
        
    except Exception as e:
        print(f"✗ 중간 학습 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Crypto RL 학습 테스트 시작\n")
    
    # 1. 빠른 학습 테스트
    success1 = quick_training_test()
    
    if success1:
        print("\n빠른 학습이 성공했습니다!")
        
        # 2. 중간 길이 학습 테스트 (선택사항)
        user_input = input("\n중간 길이 학습도 진행하시겠습니까? (y/n): ").lower().strip()
        if user_input in ['y', 'yes']:
            success2 = medium_training_test()
            if success2:
                print("\n중간 학습도 성공했습니다!")
        else:
            print("중간 학습을 건너뜁니다.")
    
    print("\n" + "="*50)
    if success1:
        print("🎉 Crypto RL 학습 시스템이 정상 작동합니다!")
        print("이제 train_crypto_rl.py를 사용해서 본격적인 학습을 진행할 수 있습니다.")
    else:
        print("❌ 학습 시스템에 문제가 있습니다.")
