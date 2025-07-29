from dataclasses import dataclass
import pandas as pd
import numpy as np
from strategy.strategy import *

class RSI_strategy(STRATEGY):
    def __init__(self, rsi_period: int = 14, oversold_threshold: float = 30, overbought_threshold: float = 70):
        super().__init__()
        self.name = "RSI Strategy"
        self.rsi_period = rsi_period                    # RSI 계산 기간 (기본 14일)
        self.oversold_threshold = oversold_threshold    # 과매도 기준점 (기본 30)
        self.overbought_threshold = overbought_threshold # 과매수 기준점 (기본 70)
        self.dataFrame = None

    def set_data(self, ticker, dataFrame):
        self.ticker = ticker
        self.dataFrame = dataFrame
        self.dataFrame['date'] = pd.to_datetime(self.dataFrame['date'], format='%Y%m%d', errors='coerce')
        self.calculate_rsi_indicators()
        return self.dataFrame

    def calculate_rsi_indicators(self):
        """RSI 및 관련 지표 계산"""
        
        # 기본 이동평균선들 (추가 확인용)
        self.dataFrame['MA5'] = self.dataFrame['close'].rolling(window=5).mean()
        self.dataFrame['MA20'] = self.dataFrame['close'].rolling(window=20).mean()
        self.dataFrame['MA60'] = self.dataFrame['close'].rolling(window=60).mean()
        
        # === RSI 계산 ===
        # 가격 변화량 계산
        self.dataFrame['price_change'] = self.dataFrame['close'].diff()
        
        # 상승/하락 분리
        self.dataFrame['gain'] = self.dataFrame['price_change'].where(self.dataFrame['price_change'] > 0, 0)
        self.dataFrame['loss'] = -self.dataFrame['price_change'].where(self.dataFrame['price_change'] < 0, 0)
        
        # 평균 상승/하락 계산 (Wilder's smoothing)
        self.dataFrame['avg_gain'] = self.dataFrame['gain'].ewm(alpha=1/self.rsi_period, adjust=False).mean()
        self.dataFrame['avg_loss'] = self.dataFrame['loss'].ewm(alpha=1/self.rsi_period, adjust=False).mean()
        
        # RS (Relative Strength) 계산
        self.dataFrame['rs'] = self.dataFrame['avg_gain'] / self.dataFrame['avg_loss']
        
        # RSI 계산
        self.dataFrame['rsi'] = 100 - (100 / (1 + self.dataFrame['rs']))
        
        # 전일 RSI 값
        self.dataFrame['rsi_prev'] = self.dataFrame['rsi'].shift(1)
        
        # RSI 기반 신호 계산
        self.dataFrame['rsi_oversold'] = self.dataFrame['rsi'] < self.oversold_threshold
        self.dataFrame['rsi_overbought'] = self.dataFrame['rsi'] > self.overbought_threshold
        
        # RSI 전일 대비 신호
        self.dataFrame['rsi_oversold_prev'] = self.dataFrame['rsi_prev'] < self.oversold_threshold
        self.dataFrame['rsi_overbought_prev'] = self.dataFrame['rsi_prev'] > self.overbought_threshold
        
        # RSI 크로스오버 신호 (과매도/과매수 구간 진입/탈출)
        # 과매도 구간 진입: 이전에는 30 이상이었는데 현재 30 이하
        self.dataFrame['rsi_oversold_entry'] = (
            (self.dataFrame['rsi_prev'] >= self.oversold_threshold) & 
            (self.dataFrame['rsi'] < self.oversold_threshold)
        )
        
        # 과매도 구간 탈출: 이전에는 30 이하였는데 현재 30 이상
        self.dataFrame['rsi_oversold_exit'] = (
            (self.dataFrame['rsi_prev'] < self.oversold_threshold) & 
            (self.dataFrame['rsi'] >= self.oversold_threshold)
        )
        
        # 과매수 구간 진입: 이전에는 70 이하였는데 현재 70 이상
        self.dataFrame['rsi_overbought_entry'] = (
            (self.dataFrame['rsi_prev'] <= self.overbought_threshold) & 
            (self.dataFrame['rsi'] > self.overbought_threshold)
        )
        
        # 과매수 구간 탈출: 이전에는 70 이상이었는데 현재 70 이하
        self.dataFrame['rsi_overbought_exit'] = (
            (self.dataFrame['rsi_prev'] > self.overbought_threshold) & 
            (self.dataFrame['rsi'] <= self.overbought_threshold)
        )
        
        # 추가 확인용 - 이동평균 정렬
        self.dataFrame['uptrend'] = (
            (self.dataFrame['MA5'] > self.dataFrame['MA20']) & 
            (self.dataFrame['MA20'] > self.dataFrame['MA60'])
        )
        
        self.dataFrame['downtrend'] = (
            (self.dataFrame['MA5'] < self.dataFrame['MA20']) & 
            (self.dataFrame['MA20'] < self.dataFrame['MA60'])
        )

    def get_dataframe(self):
        """현재 데이터프레임 반환"""
        if self.dataFrame is None:
            raise ValueError("DataFrame is not set. Please set the DataFrame using set_data() method.")
        return self.dataFrame

    def run(self, target_time=None, state=None) -> TradingSignal:
        if target_time is None:
            raise ValueError("targetTime must be provided")
        if self.dataFrame is None:
            raise ValueError("dataFrame must be set before running the strategy")
        
        # targetTime과 같은 날짜의 데이터를 가져오기
        target_date = pd.to_datetime(target_time, format='%Y%m%d', errors='coerce')
        filtered_data = self.dataFrame[self.dataFrame['date'] == target_date]
        
        if filtered_data.empty:
            raise ValueError(f"No data found for date: {target_time}")
        
        # 해당 날짜의 데이터 가져오기
        latest = filtered_data.iloc[0]  # 첫 번째 (유일한) 행
        current_price = latest['close']
        
        # RSI 관련 데이터
        rsi = latest['rsi']
        rsi_prev = latest['rsi_prev']
        rsi_oversold = latest['rsi_oversold']
        rsi_overbought = latest['rsi_overbought']
        rsi_oversold_entry = latest['rsi_oversold_entry']
        rsi_oversold_exit = latest['rsi_oversold_exit']
        rsi_overbought_entry = latest['rsi_overbought_entry']
        rsi_overbought_exit = latest['rsi_overbought_exit']
        
        # 추가 확인용
        uptrend = latest['uptrend']
        downtrend = latest['downtrend']
        
        # NaN 체크
        if pd.isna(rsi) or pd.isna(rsi_prev):
            return TradingSignal.create_hold_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price
            )
        
        # 신호 강도 계산
        buy_score = 0
        sell_score = 0
        confidence = 0.5
        position_size = 0.0
        
        # === 매수 신호 점수 계산 ===
        # RSI 과매도 구간에서 반등 신호
        if rsi_oversold_exit:  # 과매도 구간 탈출 (강력한 매수 신호)
            buy_score += 50
        
        if rsi_oversold and uptrend:  # 과매도 + 상승 추세
            buy_score += 40
        
        if rsi < 25:  # 극심한 과매도 (추가 점수)
            buy_score += 30
        elif rsi < self.oversold_threshold:  # 일반 과매도
            buy_score += 20
        
        if rsi_oversold and rsi > rsi_prev:  # 과매도 구간에서 RSI 상승
            buy_score += 25
        
        # === 매도 신호 점수 계산 ===
        # RSI 과매수 구간에서 하락 신호
        if rsi_overbought_entry:  # 과매수 구간 진입 (강력한 매도 신호)
            sell_score += 50
        
        if rsi_overbought and downtrend:  # 과매수 + 하락 추세
            sell_score += 40
        
        if rsi > 75:  # 극심한 과매수 (추가 점수)
            sell_score += 30
        elif rsi > self.overbought_threshold:  # 일반 과매수
            sell_score += 20
        
        if rsi_overbought and rsi < rsi_prev:  # 과매수 구간에서 RSI 하락
            sell_score += 25
        
        # === 신호 결정 로직 ===
        if buy_score >= 60:  # 강력한 매수 신호
            confidence = min(0.9, 0.7 + (buy_score - 60) * 0.01)
            position_size = min(1.0, (buy_score - 40) * 0.02)
            
            return TradingSignal.create_buy_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=position_size,
                confidence=confidence
            )
        
        elif sell_score >= 60:  # 강력한 매도 신호
            confidence = min(0.9, 0.7 + (sell_score - 60) * 0.01)
            position_size = min(1.0, (sell_score - 40) * 0.02)
            
            return TradingSignal.create_sell_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=position_size,
                confidence=confidence
            )
        
        elif buy_score >= 40:  # 중간 매수 신호
            confidence = 0.6
            position_size = 0.3
            
            return TradingSignal.create_buy_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=position_size,
                confidence=confidence
            )
        
        elif sell_score >= 40:  # 중간 매도 신호
            confidence = 0.6
            position_size = 0.3
            
            return TradingSignal.create_sell_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=position_size,
                confidence=confidence
            )
        
        elif buy_score >= 20:  # 약한 매수 신호
            confidence = 0.5
            position_size = 0.1
            
            return TradingSignal.create_buy_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=position_size,
                confidence=confidence
            )
        
        elif sell_score >= 20:  # 약한 매도 신호
            confidence = 0.5
            position_size = 0.1
            
            return TradingSignal.create_sell_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=position_size,
                confidence=confidence
            )
        
        else:  # 신호 없음 (홀드)
            return TradingSignal.create_hold_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price
            )
