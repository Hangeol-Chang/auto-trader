"""
Crypto Reinforcement Learning Learner

crypto 데이터를 이용한 강화학습 모델
quantylab의 ReinforcementLearner를 기반으로 crypto 거래에 특화
"""

import os
import logging
import numpy as np
import pandas as pd
import json
import sys
from datetime import datetime

# tqdm import with fallback
try:
    from tqdm import tqdm
except ImportError:
    # fallback to simple range if tqdm is not available
    def tqdm(iterable, desc="Progress"):
        print(f"{desc}...")
        return iterable

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from model.crypto_rl_environment import CryptoEnvironment
from model.crypto_rl_agent import CryptoAgent
from quantylab.networks import DNN, LSTMNetwork, CNN, DNNLSTMNetwork
from quantylab.visualizer import Visualizer
from quantylab import utils
from module.crypto.crypto_data_manager import get_candle_data


class CryptoReinforcementLearner:
    """암호화폐 강화학습 모델"""
    
    def __init__(self, market='KRW-BTC', interval='1d',
                 min_trading_price=10000, max_trading_price=1000000,
                 net='dnn', num_steps=1, lr=0.0005,
                 discount_factor=0.9, num_epochs=1000,
                 balance=1000000, start_epsilon=1,
                 output_path='model/crypto_rl_models',
                 reuse_models=True):
        
        # 인자 확인
        assert min_trading_price > 0
        assert max_trading_price > 0
        assert max_trading_price >= min_trading_price
        assert num_steps > 0
        assert lr > 0
        
        # 강화학습 설정
        self.market = market
        self.interval = interval
        self.discount_factor = discount_factor
        self.num_epochs = num_epochs
        self.start_epsilon = start_epsilon
        
        # 데이터 로드
        self.chart_data = None
        self.training_data = None
        self.load_data()
        
        # 환경 설정
        self.environment = CryptoEnvironment(self.chart_data)
        
        # 에이전트 설정
        self.agent = CryptoAgent(self.environment, balance, min_trading_price, max_trading_price)
        
        # 특성 수 계산
        self.num_features = self.agent.STATE_DIM
        if self.training_data is not None:
            self.num_features += self.training_data.shape[1]
        
        # 신경망 설정
        self.net = net
        self.num_steps = num_steps
        self.lr = lr
        self.value_network = None
        self.policy_network = None
        self.reuse_models = reuse_models
        
        # 가시화 모듈
        self.visualizer = Visualizer()
        
        # 메모리
        self.memory_sample = []
        self.memory_action = []
        self.memory_reward = []
        self.memory_value = []
        self.memory_policy = []
        self.memory_pv = []
        self.memory_num_coins = []
        self.memory_exp_idx = []
        
        # 학습 정보
        self.loss = 0.
        self.itr_cnt = 0
        self.exploration_cnt = 0
        self.batch_size = 0
        
        # 출력 경로
        self.output_path = output_path
        if not os.path.exists(output_path):
            os.makedirs(output_path)
    
    def load_data(self):
        """암호화폐 데이터 로드"""
        print(f"Loading crypto data for {self.market} with interval {self.interval}")
        
        # 캔들 데이터 로드 (최근 데이터)
        df = get_candle_data(
            market=self.market, 
            interval=self.interval,
            use_cache=True
        )
        
        if df is None or df.empty:
            raise ValueError(f"Failed to load data for {self.market}")
        
        # 최근 1000개 데이터만 사용 (메모리 효율성)
        if len(df) > 1000:
            df = df.tail(1000).reset_index(drop=True)
        
        # 필요한 컬럼만 추출하고 정렬
        required_columns = ['candle_date_time_utc', 'opening_price', 'high_price', 
                          'low_price', 'trade_price', 'candle_acc_trade_volume']
        
        df = df[required_columns].copy()
        df = df.sort_values('candle_date_time_utc').reset_index(drop=True)
        
        # 컬럼명 변경 (quantylab과 호환성)
        df.rename(columns={
            'opening_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'trade_price': 'close',
            'candle_acc_trade_volume': 'volume'
        }, inplace=True)
        
        self.chart_data = df
        
        # 기술적 지표 계산하여 training_data 생성
        self.create_training_data()
        
        print(f"Loaded {len(self.chart_data)} candles")
    
    def create_training_data(self):
        """기술적 지표를 계산하여 학습 데이터 생성"""
        df = self.chart_data.copy()
        
        # 이동평균
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        
        # RSI 계산
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD 계산
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 볼린저 밴드
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_ratio'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # 거래량 지표
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 가격 변화율
        df['price_change'] = df['close'].pct_change()
        df['price_change_5'] = df['close'].pct_change(5)
        df['price_change_20'] = df['close'].pct_change(20)
        
        # 학습에 사용할 특성 선택
        feature_columns = [
            'ma5', 'ma20', 'ma60', 'rsi', 'macd', 'macd_signal', 'macd_hist',
            'bb_ratio', 'volume_ratio', 'price_change', 'price_change_5', 'price_change_20'
        ]
        
        self.training_data = df[feature_columns].fillna(0)
        
        print(f"Created training data with {len(feature_columns)} features")
    
    def init_value_network(self, shared_network=None, activation='linear', loss='mse'):
        """가치 신경망 초기화"""
        if self.net == 'dnn':
            self.value_network = DNN(
                input_dim=self.num_features,
                output_dim=self.agent.NUM_ACTIONS,
                lr=self.lr, shared_network=shared_network,
                activation=activation, loss=loss)
        elif self.net == 'lstm':
            self.value_network = LSTMNetwork(
                input_dim=self.num_features,
                output_dim=self.agent.NUM_ACTIONS,
                lr=self.lr, num_steps=self.num_steps,
                shared_network=shared_network,
                activation=activation, loss=loss)
        elif self.net == 'cnn':
            self.value_network = CNN(
                input_dim=self.num_features,
                output_dim=self.agent.NUM_ACTIONS,
                lr=self.lr, num_steps=self.num_steps,
                shared_network=shared_network,
                activation=activation, loss=loss)
        elif self.net == 'dnn_lstm':
            self.value_network = DNNLSTMNetwork(
                input_dim=self.num_features,
                output_dim=self.agent.NUM_ACTIONS,
                lr=self.lr, num_steps=self.num_steps,
                shared_network=shared_network,
                activation=activation, loss=loss)
    
    def init_policy_network(self, shared_network=None, activation='softmax', loss='categorical_crossentropy'):
        """정책 신경망 초기화"""
        if self.net == 'dnn':
            self.policy_network = DNN(
                input_dim=self.num_features,
                output_dim=self.agent.NUM_ACTIONS,
                lr=self.lr, shared_network=shared_network,
                activation=activation, loss=loss)
        elif self.net == 'lstm':
            self.policy_network = LSTMNetwork(
                input_dim=self.num_features,
                output_dim=self.agent.NUM_ACTIONS,
                lr=self.lr, num_steps=self.num_steps,
                shared_network=shared_network,
                activation=activation, loss=loss)
        elif self.net == 'cnn':
            self.policy_network = CNN(
                input_dim=self.num_features,
                output_dim=self.agent.NUM_ACTIONS,
                lr=self.lr, num_steps=self.num_steps,
                shared_network=shared_network,
                activation=activation, loss=loss)
        elif self.net == 'dnn_lstm':
            self.policy_network = DNNLSTMNetwork(
                input_dim=self.num_features,
                output_dim=self.agent.NUM_ACTIONS,
                lr=self.lr, num_steps=self.num_steps,
                shared_network=shared_network,
                activation=activation, loss=loss)
    
    def reset(self):
        """학습 환경 초기화"""
        self.sample = None
        self.training_data_idx = -1
        # 환경 초기화
        self.environment.reset()
        # 에이전트 초기화
        self.agent.reset()
        # 메모리 초기화
        self.memory_sample = []
        self.memory_action = []
        self.memory_reward = []
        self.memory_value = []
        self.memory_policy = []
        self.memory_pv = []
        self.memory_num_coins = []
        self.memory_exp_idx = []
        self.loss = 0.
        self.itr_cnt = 0
        self.exploration_cnt = 0
        self.batch_size = 0
        
        # 하이브리드 네트워크를 위한 임시 샘플 메모리 초기화
        if hasattr(self, '_temp_samples'):
            self._temp_samples = []
    
    def build_sample(self):
        """학습 샘플 구성"""
        self.environment.observe()
        if len(self.training_data) > self.environment.idx:
            self.training_data_idx = self.environment.idx
            sample = []
            if self.training_data is not None:
                sample.extend(self.training_data.iloc[self.training_data_idx].values)
            sample.extend(self.agent.get_status())
            
            # 하이브리드 네트워크(DNN+LSTM)인 경우 시계열 형태로 구성
            if self.net == 'dnn_lstm':
                # 현재까지의 샘플들을 이용해 시계열 시퀀스 구성
                current_sample = np.array(sample, dtype=np.float32)
                
                # 메모리에 현재 샘플 임시 저장
                if not hasattr(self, '_temp_samples'):
                    self._temp_samples = []
                self._temp_samples.append(current_sample)
                
                # num_steps만큼의 시퀀스 구성
                if len(self._temp_samples) >= self.num_steps:
                    sequence = self._temp_samples[-self.num_steps:]
                else:
                    # 데이터가 부족한 경우 현재 샘플로 패딩
                    sequence = [current_sample] * (self.num_steps - len(self._temp_samples)) + self._temp_samples
                
                self.sample = np.array(sequence, dtype=np.float32)
            else:
                self.sample = np.array(sample, dtype=np.float32)
                
            return self.sample
        return None
    
    def get_batch(self, batch_size, delayed_reward):
        """배치 데이터 구성"""
        memory = zip(
            reversed(self.memory_sample[-batch_size:]),
            reversed(self.memory_action[-batch_size:]),
            reversed(self.memory_value[-batch_size:]),
            reversed(self.memory_policy[-batch_size:]),
        )
        
        # 하이브리드 네트워크(DNN+LSTM)인 경우 시계열 형태로 데이터 구성
        if self.net == 'dnn_lstm':
            x = np.zeros((batch_size, self.num_steps, self.num_features))
        else:
            x = np.zeros((batch_size, self.num_features))
            
        y_value = np.zeros((batch_size, self.agent.NUM_ACTIONS))
        y_policy = np.zeros((batch_size, self.agent.NUM_ACTIONS))
        
        value_max_next = 0
        reward_next = delayed_reward
        
        for i, (sample, action, value, policy) in enumerate(memory):
            if self.net == 'dnn_lstm':
                # 하이브리드 네트워크의 경우 샘플이 이미 시계열 형태임
                if len(sample.shape) == 2 and sample.shape[0] == self.num_steps:
                    # 이미 올바른 시계열 형태: (num_steps, features)
                    x[i] = sample
                else:
                    # 1D 샘플인 경우 시계열 형태로 변환
                    # 같은 샘플을 num_steps만큼 반복
                    sample_1d = sample.flatten() if len(sample.shape) > 1 else sample
                    sequence = np.tile(sample_1d, (self.num_steps, 1))
                    x[i] = sequence
            else:
                x[i] = sample
                
            r = self.memory_reward[-batch_size + i]
            y_value[i] = value
            y_policy[i] = policy
            
            reward = r + self.discount_factor * reward_next
            y_value[i, action] = reward
            reward_next = reward
            
            y_policy[i, action] = 1  # 선택한 행동에 대해서만 1
        
        return x, y_value, y_policy
    
    def fit(self, num_epoches=1000, max_memory=60, balance=1000000,
            discount_factor=0.9, start_epsilon=0.5, learning=True):
        """모델 학습"""
        
        print(f"Starting crypto RL training for {self.market}")
        print(f"Epochs: {num_epoches}, Balance: {balance:,}")
        print(f"Chart data length: {len(self.chart_data)}")
        
        # 신경망 초기화
        if self.value_network is None:
            self.init_value_network()
        if self.policy_network is None:
            self.init_policy_network()
        
        # 최대 포트폴리오 가치 기록을 위한 변수
        max_portfolio_value = 0
        epoch_summary = []
        
        for epoch in tqdm(range(num_epoches), desc="Training"):
            # 환경 초기화
            self.reset()
            self.agent.set_balance(balance)
            
            # 탐험 비율 계산 (점진적 감소)
            if learning:
                epsilon = start_epsilon * (1. - float(epoch) / (num_epoches - 1))
            else:
                epsilon = 0.
            
            step_count = 0
            max_steps = len(self.chart_data) - 1  # 최대 스텝 제한
            
            while step_count < max_steps:
                # 다음 샘플 생성
                next_sample = self.build_sample()
                if next_sample is None:
                    break
                
                step_count += 1
                
                # 신경망 예측
                pred_value = None
                pred_policy = None
                if self.value_network is not None:
                    pred_value = self.value_network.predict(next_sample)
                if self.policy_network is not None:
                    pred_policy = self.policy_network.predict(next_sample)
                
                # 행동 결정
                action, confidence, exploration = self.agent.decide_action(
                    pred_value, pred_policy, epsilon)
                
                # 행동 수행
                immediate_reward = self.agent.act(action, confidence)
                
                # 메모리에 저장
                self.memory_sample.append(next_sample)
                self.memory_action.append(action)
                self.memory_reward.append(immediate_reward)
                if self.value_network is not None:
                    self.memory_value.append(pred_value)
                else:
                    self.memory_value.append([0] * self.agent.NUM_ACTIONS)
                if self.policy_network is not None:
                    self.memory_policy.append(pred_policy)
                else:
                    self.memory_policy.append([0] * self.agent.NUM_ACTIONS)
                self.memory_pv.append(self.agent.portfolio_value)
                self.memory_num_coins.append(self.agent.num_coins)
                if exploration:
                    self.memory_exp_idx.append(self.itr_cnt)
                
                self.batch_size += 1
                self.itr_cnt += 1
                self.exploration_cnt += 1 if exploration else 0
                
                # 진행 상황 체크 (너무 오래 걸리면 중단)
                if step_count % 100 == 0:
                    print(f"Epoch {epoch}, Step {step_count}/{max_steps}")
            
            # 에포크 종료 후 학습
            if learning and self.batch_size > 0:
                # 지연 보상 계산
                delayed_reward = self.agent.profitloss
                
                # 배치 학습
                batch_size = min(self.batch_size, max_memory)
                x, y_value, y_policy = self.get_batch(batch_size, delayed_reward)
                
                if self.value_network is not None:
                    loss = self.value_network.train_on_batch(x, y_value)
                    self.loss += loss
                if self.policy_network is not None:
                    loss = self.policy_network.train_on_batch(x, y_policy)
                    self.loss += loss
            
            # 최대 포트폴리오 가치 갱신
            if self.agent.portfolio_value > max_portfolio_value:
                max_portfolio_value = self.agent.portfolio_value
            
            # 에포크 요약 저장
            epoch_summary.append({
                'epoch': epoch,
                'epsilon': epsilon,
                'exploration_cnt': self.exploration_cnt,
                'itr_cnt': self.itr_cnt,
                'loss': self.loss,
                'portfolio_value': self.agent.portfolio_value,
                'profitloss': self.agent.profitloss,
                'num_buy': self.agent.num_buy,
                'num_sell': self.agent.num_sell,
                'num_hold': self.agent.num_hold,
                'steps': step_count
            })
            
            # 에포크별 결과 출력
            print(f"Epoch {epoch:3d}: Steps={step_count:3d}, Portfolio={self.agent.portfolio_value:,.0f}, "
                  f"P&L={self.agent.profitloss:6.4f}, Actions(B/S/H)={self.agent.num_buy}/{self.agent.num_sell}/{self.agent.num_hold}")
        
        # 학습 결과 저장
        self.save_results(epoch_summary, max_portfolio_value)
        
        return epoch_summary
    
    def save_results(self, epoch_summary, max_portfolio_value):
        """학습 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 요약 정보 저장
        summary_file = os.path.join(self.output_path, f"training_summary_{self.market}_{timestamp}.json")
        with open(summary_file, 'w') as f:
            json.dump({
                'market': self.market,
                'interval': self.interval,
                'max_portfolio_value': max_portfolio_value,
                'final_portfolio_value': self.agent.portfolio_value,
                'final_profitloss': self.agent.profitloss,
                'num_epochs': len(epoch_summary),
                'epoch_summary': epoch_summary
            }, f, indent=2)
        
        # 마지막 요약 파일 경로 저장
        self._last_summary_path = summary_file
        
        # 모델 저장
        if self.value_network is not None:
            value_model_path = os.path.join(self.output_path, f"value_network_{self.market.replace('-', '_')}_{timestamp}.weights.h5")
            self.value_network.save_model(value_model_path)
        
        if self.policy_network is not None:
            policy_model_path = os.path.join(self.output_path, f"policy_network_{self.market.replace('-', '_')}_{timestamp}.weights.h5")
            self.policy_network.save_model(policy_model_path)
        
        print(f"\nTraining completed!")
        print(f"Results saved to: {summary_file}")
        print(f"Max Portfolio Value: {max_portfolio_value:,.0f}")
        print(f"Final P&L: {self.agent.profitloss:6.4f}")
    
    def predict(self, sample):
        """예측 수행"""
        pred_value = None
        pred_policy = None
        
        if self.value_network is not None:
            pred_value = self.value_network.predict(sample)
        if self.policy_network is not None:
            pred_policy = self.policy_network.predict(sample)
        
        return pred_value, pred_policy
    
    def save_model(self, model_path, summary_path):
        """모델과 요약 정보를 지정된 경로에 저장"""
        # 가치 네트워크 모델 저장
        if self.value_network is not None:
            self.value_network.save_model(model_path)
            print(f"Value network saved: {model_path}")
        
        # 요약 정보가 이미 저장되어 있으면 복사
        if hasattr(self, '_last_summary_path') and os.path.exists(self._last_summary_path):
            import shutil
            shutil.copy2(self._last_summary_path, summary_path)
            print(f"Summary copied: {summary_path}")
        else:
            print(f"Warning: Summary file not found, using default location")
