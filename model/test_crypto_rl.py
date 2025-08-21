"""
Crypto Reinforcement Learning Test Script

crypto 강화학습 모델을 테스트하는 스크립트
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from model.crypto_rl_learner import CryptoReinforcementLearner
from module.crypto.crypto_data_manager import get_upbit_markets


def test_crypto_rl_basic():
    """기본 crypto RL 테스트"""
    print("=== Crypto Reinforcement Learning Basic Test ===")
    
    # 테스트 설정
    market = 'KRW-BTC'
    interval = '1d'
    balance = 1000000  # 100만원
    
    try:
        # 학습자 생성
        learner = CryptoReinforcementLearner(
            market=market,
            interval=interval,
            balance=balance,
            num_epochs=10,  # 테스트용으로 적은 에포크
            min_trading_price=50000,    # 5만원
            max_trading_price=500000,   # 50만원
            net='dnn',
            lr=0.001,
            start_epsilon=0.8
        )
        
        print(f"Market: {market}")
        print(f"Interval: {interval}")
        print(f"Chart data shape: {learner.chart_data.shape}")
        print(f"Training data shape: {learner.training_data.shape}")
        print(f"Number of features: {learner.num_features}")
        
        # 학습 실행
        print("\nStarting training...")
        epoch_summary = learner.fit(
            num_epoches=10,
            balance=balance,
            learning=True
        )
        
        # 결과 출력
        final_summary = epoch_summary[-1]
        print("\n=== Training Results ===")
        print(f"Initial Balance: {balance:,}")
        print(f"Final Portfolio Value: {final_summary['portfolio_value']:,.0f}")
        print(f"Final P&L: {final_summary['profitloss']:6.4f} ({final_summary['profitloss']*100:6.2f}%)")
        print(f"Total Buy Actions: {final_summary['num_buy']}")
        print(f"Total Sell Actions: {final_summary['num_sell']}")
        print(f"Total Hold Actions: {final_summary['num_hold']}")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_cryptos():
    """여러 암호화폐에 대한 테스트"""
    print("\n=== Multiple Crypto Test ===")
    
    # 주요 암호화폐 목록
    test_markets = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP']
    results = {}
    
    for market in test_markets:
        print(f"\nTesting {market}...")
        try:
            learner = CryptoReinforcementLearner(
                market=market,
                interval='1d',
                balance=1000000,
                num_epochs=5,
                min_trading_price=10000,
                max_trading_price=200000,
                net='dnn'
            )
            
            epoch_summary = learner.fit(num_epoches=5, learning=True)
            final_result = epoch_summary[-1]
            
            results[market] = {
                'portfolio_value': final_result['portfolio_value'],
                'profitloss': final_result['profitloss'],
                'success': True
            }
            
            print(f"{market} - P&L: {final_result['profitloss']:6.4f}")
            
        except Exception as e:
            print(f"{market} - Failed: {e}")
            results[market] = {'success': False, 'error': str(e)}
    
    # 결과 요약
    print("\n=== Multiple Crypto Test Results ===")
    for market, result in results.items():
        if result['success']:
            print(f"{market}: P&L {result['profitloss']:6.4f} ({result['profitloss']*100:6.2f}%)")
        else:
            print(f"{market}: Failed - {result.get('error', 'Unknown error')}")
    
    return results


def test_different_networks():
    """다른 신경망 구조 테스트"""
    print("\n=== Different Network Test ===")
    
    networks = ['dnn', 'lstm', 'cnn']
    market = 'KRW-BTC'
    results = {}
    
    for net in networks:
        print(f"\nTesting {net.upper()} network...")
        try:
            learner = CryptoReinforcementLearner(
                market=market,
                interval='1d',
                balance=1000000,
                num_epochs=5,
                net=net,
                num_steps=5 if net in ['lstm', 'cnn'] else 1
            )
            
            epoch_summary = learner.fit(num_epoches=5, learning=True)
            final_result = epoch_summary[-1]
            
            results[net] = {
                'portfolio_value': final_result['portfolio_value'],
                'profitloss': final_result['profitloss'],
                'success': True
            }
            
            print(f"{net.upper()} - P&L: {final_result['profitloss']:6.4f}")
            
        except Exception as e:
            print(f"{net.upper()} - Failed: {e}")
            results[net] = {'success': False, 'error': str(e)}
    
    # 결과 요약
    print("\n=== Network Comparison Results ===")
    for net, result in results.items():
        if result['success']:
            print(f"{net.upper()}: P&L {result['profitloss']:6.4f} ({result['profitloss']*100:6.2f}%)")
        else:
            print(f"{net.upper()}: Failed - {result.get('error', 'Unknown error')}")
    
    return results


def test_prediction_mode():
    """예측 모드 테스트 (학습 없이 랜덤 행동)"""
    print("\n=== Prediction Mode Test ===")
    
    market = 'KRW-BTC'
    
    try:
        learner = CryptoReinforcementLearner(
            market=market,
            interval='1d',
            balance=1000000,
            num_epochs=1
        )
        
        # 학습 없이 예측만 수행 (랜덤 행동)
        print("Running prediction mode (no learning, random actions)...")
        epoch_summary = learner.fit(num_epoches=1, learning=False)
        
        final_result = epoch_summary[-1]
        print(f"Random trading result - P&L: {final_result['profitloss']:6.4f}")
        
        return True
        
    except Exception as e:
        print(f"Prediction mode test failed: {e}")
        return False


def run_all_tests():
    """모든 테스트 실행"""
    print("Starting Crypto Reinforcement Learning Tests...")
    print("=" * 60)
    
    test_results = {}
    
    # 기본 테스트
    test_results['basic'] = test_crypto_rl_basic()
    
    # 예측 모드 테스트
    test_results['prediction'] = test_prediction_mode()
    
    # 여러 암호화폐 테스트 (시간이 오래 걸릴 수 있음)
    # test_results['multiple_cryptos'] = test_multiple_cryptos()
    
    # 다른 신경망 테스트 (시간이 오래 걸릴 수 있음)
    # test_results['different_networks'] = test_different_networks()
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    for test_name, result in test_results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
    
    return test_results


if __name__ == "__main__":
    # 실행할 테스트 선택
    import argparse
    parser = argparse.ArgumentParser(description='Crypto RL Test Script')
    parser.add_argument('--test', choices=['basic', 'multiple', 'networks', 'prediction', 'all'], 
                       default='basic', help='Test to run')
    
    args = parser.parse_args()
    
    if args.test == 'basic':
        test_crypto_rl_basic()
    elif args.test == 'multiple':
        test_multiple_cryptos()
    elif args.test == 'networks':
        test_different_networks()
    elif args.test == 'prediction':
        test_prediction_mode()
    elif args.test == 'all':
        run_all_tests()
