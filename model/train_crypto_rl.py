"""
Crypto RL Training Script

실제 crypto 강화학습 모델을 학습시키는 스크립트
"""

import os
import sys
import argparse
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from model.crypto_rl_learner import CryptoReinforcementLearner


def train_crypto_model(market='KRW-BTC', interval='1m', epochs=200, 
                      balance=10000000, net='dnn', lr=0.0005):
    """Crypto 강화학습 모델 학습"""
    
    print(f"=== Crypto RL Training ===")
    print(f"Market: {market}")
    print(f"Interval: {interval}")
    print(f"Epochs: {epochs}")
    print(f"Initial Balance: {balance:,}")
    print(f"Network: {net}")
    print(f"Learning Rate: {lr}")
    print("=" * 50)
    
    try:
        # 학습자 생성
        learner = CryptoReinforcementLearner(
            market=market,
            interval=interval,
            balance=balance,
            num_epochs=epochs,
            min_trading_price=100000,    # 10만원
            max_trading_price=2000000,   # 200만원
            net=net,
            lr=lr,
            start_epsilon=0.9,
            discount_factor=0.95,
            output_path=f'model/crypto_rl_models/{market.replace("-", "_")}'
        )
        
        print(f"Data loaded: {len(learner.chart_data)} candles")
        print(f"Features: {learner.num_features}")
        
        # 학습 실행
        epoch_summary = learner.fit(
            num_epoches=epochs,
            balance=balance,
            learning=True,
            start_epsilon=0.9
        )
        
        # 최종 결과 출력
        final_result = epoch_summary[-1]
        print("\n" + "=" * 50)
        print("Training Completed!")
        print(f"Initial Balance: {balance:,}")
        print(f"Final Portfolio Value: {final_result['portfolio_value']:,.0f}")
        print(f"Final P&L: {final_result['profitloss']:6.4f} ({final_result['profitloss']*100:6.2f}%)")
        print(f"Total Actions - Buy: {final_result['num_buy']}, Sell: {final_result['num_sell']}, Hold: {final_result['num_hold']}")
        
        return learner, epoch_summary
        
    except Exception as e:
        print(f"Training failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def main():
    parser = argparse.ArgumentParser(description='Crypto Reinforcement Learning Training')
    parser.add_argument('--market', default='KRW-BTC', help='Crypto market (e.g., KRW-BTC)')
    parser.add_argument('--interval', default='1m', choices=['1m', '5m', '15m', '30m', '1h', '4h', '1d'], 
                       help='Candle interval')
    parser.add_argument('--epochs', type=int, default=1000, help='Number of training epochs')
    parser.add_argument('--balance', type=int, default=10000000, help='Initial balance (KRW)')
    parser.add_argument('--net', default='dnn', choices=['dnn', 'lstm', 'cnn'], 
                       help='Neural network type')
    parser.add_argument('--lr', type=float, default=0.0005, help='Learning rate')
    
    args = parser.parse_args()
    
    # 학습 실행
    learner, summary = train_crypto_model(
        market=args.market,
        interval=args.interval,
        epochs=args.epochs,
        balance=args.balance,
        net=args.net,
        lr=args.lr
    )
    
    if learner is not None:
        print(f"\nModel training completed successfully!")
        print(f"Models saved in: {learner.output_path}")
    else:
        print("Training failed!")


if __name__ == "__main__":
    main()
