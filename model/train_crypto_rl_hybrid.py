"""
Crypto DNN+LSTM 하이브리드 모델 학습 스크립트

DNN의 특성 추출 능력과 LSTM의 시계열 패턴 학습 능력을 결합한 
하이브리드 신경망으로 암호화폐 거래 AI 모델 학습
"""

import os
import sys
import argparse
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from model.crypto_rl_learner import CryptoReinforcementLearner


def train_hybrid_model(market='KRW-BTC', epochs=100, balance=10000000, 
                      num_steps=10, lr=0.0003, output_path='model/crypto_rl_models'):
    """
    DNN+LSTM 하이브리드 모델 학습
    
    Args:
        market (str): 암호화폐 마켓 (예: KRW-BTC, KRW-ETH)
        epochs (int): 학습 에포크 수
        balance (int): 초기 자본금
        num_steps (int): LSTM을 위한 시계열 스텝 수
        lr (float): 학습률
        output_path (str): 모델 저장 경로
    """
    
    print("🚀 DNN+LSTM 하이브리드 암호화폐 거래 AI 학습 시작")
    print(f"📊 마켓: {market}")
    print(f"🧠 네트워크: DNN+LSTM 하이브리드")
    print(f"📈 에포크: {epochs}")
    print(f"💰 초기 자본: {balance:,} 원")
    print(f"⏱️  시계열 스텝: {num_steps}")
    print(f"🎯 학습률: {lr}")
    print("-" * 50)
    
    # 하이브리드 학습기 초기화
    learner = CryptoReinforcementLearner(
        market=market,
        interval='1d',
        min_trading_price=10000,
        max_trading_price=1000000,
        net='dnn_lstm',  # 하이브리드 네트워크 사용
        num_steps=num_steps,
        lr=lr,
        discount_factor=0.9,
        num_epochs=epochs,
        balance=balance,
        start_epsilon=1.0,
        output_path=output_path,
        reuse_models=False
    )
    
    try:
        # 데이터 로드
        print("📥 암호화폐 데이터 로딩 중...")
        learner.load_data()
        
        # 학습 실행
        print("🎓 하이브리드 모델 학습 시작...")
        learner.fit()
        
        print("✅ 하이브리드 모델 학습 완료!")
        
        # 학습 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 모델 파일명 생성
        market_code = market.replace('-', '_')
        model_filename = f"hybrid_network_{market_code}_{timestamp}.weights.h5"
        summary_filename = f"hybrid_summary_{market}_{timestamp}.json"
        
        # 모델 저장
        model_path = os.path.join(output_path, model_filename)
        summary_path = os.path.join(output_path, summary_filename)
        
        learner.save_model(model_path, summary_path)
        
        print(f"💾 모델 저장 완료:")
        print(f"   모델: {model_path}")
        print(f"   요약: {summary_path}")
        
        return model_path, summary_path
        
    except Exception as e:
        print(f"❌ 학습 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def main():
    parser = argparse.ArgumentParser(description='DNN+LSTM 하이브리드 암호화폐 거래 AI 학습')
    
    parser.add_argument('--market', type=str, default='KRW-BTC',
                        help='암호화폐 마켓 (기본값: KRW-BTC)')
    
    parser.add_argument('--epochs', type=int, default=100,
                        help='학습 에포크 수 (기본값: 100)')
    
    parser.add_argument('--balance', type=int, default=10000000,
                        help='초기 자본금 (기본값: 10,000,000원)')
    
    parser.add_argument('--num-steps', type=int, default=10,
                        help='LSTM 시계열 스텝 수 (기본값: 10)')
    
    parser.add_argument('--lr', type=float, default=0.0003,
                        help='학습률 (기본값: 0.0003)')
    
    parser.add_argument('--output', type=str, default='model/crypto_rl_models',
                        help='모델 저장 경로 (기본값: model/crypto_rl_models)')
    
    args = parser.parse_args()
    
    # 하이브리드 모델 학습 실행
    model_path, summary_path = train_hybrid_model(
        market=args.market,
        epochs=args.epochs,
        balance=args.balance,
        num_steps=args.num_steps,
        lr=args.lr,
        output_path=args.output
    )
    
    if model_path and summary_path:
        print("\n🎉 하이브리드 모델 학습이 성공적으로 완료되었습니다!")
        print(f"\n📊 학습된 모델을 사용하여 예측을 실행하려면:")
        print(f"python model/predict_crypto_signals.py --market {args.market} --candles 30")
        
        print(f"\n🔄 모델 성능을 비교하려면:")
        print(f"python model/compare_models.py --market {args.market}")
    else:
        print("\n❌ 하이브리드 모델 학습이 실패했습니다.")


if __name__ == "__main__":
    main()
