"""
Crypto RL Model Loader

저장된 crypto 강화학습 모델을 로드하고 사용하는 클래스
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from model.crypto_rl_learner import CryptoReinforcementLearner
from model.crypto_rl_agent import CryptoAgent
from model.crypto_rl_environment import CryptoEnvironment
from module.crypto.crypto_data_manager import get_candle_data


class CryptoRLModelLoader:
    """저장된 Crypto RL 모델을 로드하고 예측에 사용하는 클래스"""
    
    def __init__(self, model_path: str, summary_path: str):
        """
        Args:
            model_path: 저장된 모델 파일 경로 (.weights.h5)
            summary_path: 학습 요약 파일 경로 (.json)
        """
        self.model_path = model_path
        self.summary_path = summary_path
        self.learner = None
        self.training_summary = None
        
        self.load_training_summary()
        self.setup_learner()
        self.load_model()
    
    def load_training_summary(self):
        """학습 요약 정보 로드"""
        with open(self.summary_path, 'r', encoding='utf-8') as f:
            self.training_summary = json.load(f)
        
        print(f"모델 정보:")
        print(f"  마켓: {self.training_summary['market']}")
        print(f"  간격: {self.training_summary['interval']}")
        print(f"  학습 에포크: {self.training_summary['num_epochs']}")
        print(f"  최고 포트폴리오: {self.training_summary['max_portfolio_value']:,.0f}")
        print(f"  최종 손익률: {self.training_summary['final_profitloss']:.4f}")
    
    def setup_learner(self):
        """학습자 설정 (모델 구조 재생성)"""
        self.learner = CryptoReinforcementLearner(
            market=self.training_summary['market'],
            interval=self.training_summary['interval'],
            balance=1000000,  # 예측용이므로 기본값
            num_epochs=1,     # 학습하지 않으므로 1
            min_trading_price=100000,
            max_trading_price=1000000,
            net='dnn',        # 저장된 모델과 같은 구조
            reuse_models=False
        )
        
        # 신경망 초기화 (구조만 생성)
        self.learner.init_value_network()
        print(f"✓ 학습자 설정 완료")
    
    def load_model(self):
        """저장된 모델 가중치 로드"""
        try:
            self.learner.value_network.load_model(self.model_path)
            print(f"✓ 모델 로드 완료: {self.model_path}")
        except Exception as e:
            print(f"✗ 모델 로드 실패: {e}")
            raise
    
    def predict_single(self, market_data: pd.DataFrame, current_idx: int) -> Tuple[int, float, bool]:
        """
        단일 시점에 대한 예측 수행
        
        Args:
            market_data: 시장 데이터 (OHLCV)
            current_idx: 현재 인덱스
            
        Returns:
            (action, confidence, exploration): 행동, 신뢰도, 탐험 여부
        """
        # 환경 설정
        self.learner.environment = CryptoEnvironment(market_data)
        self.learner.environment.idx = current_idx
        self.learner.environment.observation = market_data.iloc[current_idx]
        
        # 학습 데이터 인덱스 설정
        self.learner.training_data_idx = current_idx
        
        # 샘플 구성
        sample = []
        if self.learner.training_data is not None and current_idx < len(self.learner.training_data):
            sample.extend(self.learner.training_data.iloc[current_idx].values)
        
        # 에이전트 상태 추가 (기본값)
        sample.extend([0.0, 0.0, 0.0])  # ratio_hold, profitloss, price_change_ratio
        
        sample = np.array(sample, dtype=np.float32)
        
        # 예측 수행
        pred_value = self.learner.value_network.predict(sample)
        
        # 행동 결정 (탐험 없이)
        action = np.argmax(pred_value)
        confidence = pred_value[action]
        
        return action, float(confidence), False
    
    def predict_sequence(self, market: str, interval: str = '1m', 
                        last_n_candles: int = 100) -> pd.DataFrame:
        """
        최근 N개 캔들에 대한 연속 예측 수행
        
        Args:
            market: 마켓 코드 (예: KRW-BTC)
            interval: 캔들 간격
            last_n_candles: 예측할 캔들 수
            
        Returns:
            예측 결과 DataFrame
        """
        # 최신 데이터 로드
        df = get_candle_data(market, interval)
        if df is None or len(df) < last_n_candles:
            raise ValueError(f"충분한 데이터를 로드할 수 없습니다.")
        
        # 최근 N개 캔들만 사용
        recent_data = df.tail(last_n_candles).copy().reset_index(drop=True)
        
        # 컬럼명 변경
        recent_data.rename(columns={
            'opening_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'trade_price': 'close',
            'candle_acc_trade_volume': 'volume'
        }, inplace=True)
        
        # 기술적 지표 계산 (learner와 동일한 방식)
        self.learner.chart_data = recent_data
        self.learner.create_training_data()
        
        # 예측 결과 저장
        predictions = []
        
        print(f"최근 {last_n_candles}개 캔들에 대한 예측 수행...")
        
        for i in range(len(recent_data)):
            try:
                action, confidence, exploration = self.predict_single(recent_data, i)
                
                # 행동 이름 변환
                action_names = ['매수', '매도', '관망']
                action_name = action_names[action]
                
                predictions.append({
                    'datetime': recent_data.iloc[i]['candle_date_time_utc'],
                    'close_price': recent_data.iloc[i]['close'],
                    'predicted_action': action,
                    'action_name': action_name,
                    'confidence': confidence,
                    'exploration': exploration
                })
                
            except Exception as e:
                print(f"인덱스 {i}에서 예측 실패: {e}")
                continue
        
        result_df = pd.DataFrame(predictions)
        print(f"✓ {len(result_df)}개 예측 완료")
        
        return result_df
    
    def get_model_performance(self) -> dict:
        """모델 성능 정보 반환"""
        if not self.training_summary:
            return {}
        
        epoch_data = self.training_summary['epoch_summary']
        profits = [epoch['profitloss'] for epoch in epoch_data]
        
        return {
            'max_profit': max(profits),
            'min_profit': min(profits),
            'final_profit': profits[-1],
            'avg_profit': sum(profits) / len(profits),
            'total_epochs': len(epoch_data),
            'market': self.training_summary['market'],
            'interval': self.training_summary['interval']
        }


def list_available_models(models_dir: str = "model/crypto_rl_models") -> list:
    """사용 가능한 모델 목록 반환"""
    if not os.path.exists(models_dir):
        return []
    
    models = []
    
    # JSON 파일 (학습 요약) 기준으로 모델 찾기
    for file in os.listdir(models_dir):
        if file.endswith('.json') and 'training_summary' in file:
            json_path = os.path.join(models_dir, file)
            
            # 파일명 파싱: training_summary_KRW-BTC_20250821_211833.json
            parts = file.replace('.json', '').split('_')
            if len(parts) >= 4:
                # KRW-BTC에서 KRW_BTC로 변환
                market_part = '_'.join(parts[2:-2])  # KRW-BTC
                timestamp = '_'.join(parts[-2:])     # 20250821_211833
                
                # 모델 파일명 생성 (KRW-BTC -> KRW_BTC)
                market_for_filename = market_part.replace('-', '_')
                value_model = f"value_network_{market_for_filename}_{timestamp}.weights.h5"
                value_path = os.path.join(models_dir, value_model)
                
                if os.path.exists(value_path):
                    models.append({
                        'summary_path': json_path,
                        'model_path': value_path,
                        'market': market_part,  # KRW-BTC 형태 유지
                        'timestamp': timestamp
                    })
    
    return models


if __name__ == "__main__":
    # 사용 가능한 모델 목록 출력
    print("=== 사용 가능한 모델 목록 ===")
    models = list_available_models()
    
    if not models:
        print("저장된 모델이 없습니다.")
    else:
        for i, model in enumerate(models):
            print(f"{i+1}. {model['market']} - {model['timestamp']}")
        
        # 가장 최신 모델로 테스트
        latest_model = models[-1]
        print(f"\n가장 최신 모델로 테스트: {latest_model['market']}")
        
        try:
            loader = CryptoRLModelLoader(
                latest_model['model_path'],
                latest_model['summary_path']
            )
            
            # 성능 정보 출력
            performance = loader.get_model_performance()
            print(f"\n모델 성능:")
            print(f"  최고 수익률: {performance['max_profit']:.4f}")
            print(f"  최저 수익률: {performance['min_profit']:.4f}")
            print(f"  평균 수익률: {performance['avg_profit']:.4f}")
            
            # 최근 10개 캔들 예측
            print(f"\n최근 10개 캔들 예측 수행...")
            predictions = loader.predict_sequence(
                performance['market'], 
                performance['interval'], 
                10
            )
            
            print(f"\n예측 결과:")
            for _, row in predictions.tail(5).iterrows():
                print(f"  {row['datetime']}: {row['action_name']} (신뢰도: {row['confidence']:.3f})")
                
        except Exception as e:
            print(f"모델 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
