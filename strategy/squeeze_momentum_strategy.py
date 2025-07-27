from dataclasses import dataclass
import pandas as pd
import numpy as np
from strategy.strategy import *

class SqueezeMomentum_strategy(STRATEGY):
    def __init__(self, bb_period: int = 20, bb_multiplier: float = 2.0, kc_period: int = 20, kc_multiplier: float = 1.5):
        super().__init__()
        self.name = "Squeeze Momentum Strategy"
        self.bb_period = bb_period              # Bollinger Bands 기간
        self.bb_multiplier = bb_multiplier      # Bollinger Bands 배수
        self.kc_period = kc_period              # Keltner Channel 기간
        self.kc_multiplier = kc_multiplier      # Keltner Channel 배수
        self.dataFrame = None

    def set_data(self, ticker, dataFrame):
        self.ticker = ticker
        self.dataFrame = dataFrame
        self.dataFrame['date'] = pd.to_datetime(self.dataFrame['date'], format='%Y%m%d', errors='coerce')
        self.calculate_squeeze_indicators()

        print(self.dataFrame)
        return self.dataFrame

    def calculate_squeeze_indicators(self):
        """Squeeze Momentum 관련 지표 계산"""
        
        # 기본 이동평균선들
        self.dataFrame['MA20'] = self.dataFrame['close'].rolling(window=20).mean()
        self.dataFrame['MA50'] = self.dataFrame['close'].rolling(window=50).mean()
        
        # === Bollinger Bands 계산 ===
        bb_ma = self.dataFrame['close'].rolling(window=self.bb_period).mean()
        bb_std = self.dataFrame['close'].rolling(window=self.bb_period).std()
        self.dataFrame['BB_upper'] = bb_ma + (bb_std * self.bb_multiplier)
        self.dataFrame['BB_lower'] = bb_ma - (bb_std * self.bb_multiplier)
        self.dataFrame['BB_middle'] = bb_ma
        
        # === Keltner Channels 계산 ===
        # True Range 계산
        self.dataFrame['high_prev'] = self.dataFrame['high'].shift(1)
        self.dataFrame['low_prev'] = self.dataFrame['low'].shift(1)
        self.dataFrame['close_prev'] = self.dataFrame['close'].shift(1)
        
        self.dataFrame['tr1'] = self.dataFrame['high'] - self.dataFrame['low']
        self.dataFrame['tr2'] = abs(self.dataFrame['high'] - self.dataFrame['close_prev'])
        self.dataFrame['tr3'] = abs(self.dataFrame['low'] - self.dataFrame['close_prev'])
        self.dataFrame['true_range'] = self.dataFrame[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # Average True Range (ATR)
        self.dataFrame['ATR'] = self.dataFrame['true_range'].rolling(window=self.kc_period).mean()
        
        # Keltner Channels
        kc_ma = self.dataFrame['close'].rolling(window=self.kc_period).mean()
        self.dataFrame['KC_upper'] = kc_ma + (self.dataFrame['ATR'] * self.kc_multiplier)
        self.dataFrame['KC_lower'] = kc_ma - (self.dataFrame['ATR'] * self.kc_multiplier)
        self.dataFrame['KC_middle'] = kc_ma
        
        # === Squeeze 감지 ===
        # Squeeze: Bollinger Bands가 Keltner Channels 안에 있을 때
        bb_lower_valid = pd.notna(self.dataFrame['BB_lower'])
        bb_upper_valid = pd.notna(self.dataFrame['BB_upper'])
        kc_lower_valid = pd.notna(self.dataFrame['KC_lower'])
        kc_upper_valid = pd.notna(self.dataFrame['KC_upper'])
        
        # 모든 값이 유효한 경우만 계산
        valid_data = bb_lower_valid & bb_upper_valid & kc_lower_valid & kc_upper_valid
        
        self.dataFrame['squeeze_on'] = False  # 기본값
        self.dataFrame.loc[valid_data, 'squeeze_on'] = (
            (self.dataFrame.loc[valid_data, 'BB_lower'] > self.dataFrame.loc[valid_data, 'KC_lower']) & 
            (self.dataFrame.loc[valid_data, 'BB_upper'] < self.dataFrame.loc[valid_data, 'KC_upper'])
        )
        
        # === Momentum 계산 ===
        # Linear regression을 이용한 momentum 계산 (20일 기준)
        momentum_period = 20
        
        def calculate_momentum(series, period):
            """Linear regression slope를 이용한 momentum 계산"""
            momentum_values = []
            for i in range(len(series)):
                if i < period - 1:
                    momentum_values.append(np.nan)
                else:
                    y = series.iloc[i-period+1:i+1].values
                    x = np.arange(period)
                    if len(y) == period and not np.isnan(y).any():
                        # 선형 회귀 기울기 계산
                        slope = np.polyfit(x, y, 1)[0]
                        momentum_values.append(slope)
                    else:
                        momentum_values.append(np.nan)
            return momentum_values
        
        # Close price의 momentum 계산
        momentum_values = calculate_momentum(self.dataFrame['close'], momentum_period)
        self.dataFrame['momentum'] = momentum_values
        
        # === 추가 신호들 ===
        # Squeeze 시작/종료 감지 (NaN 값 안전 처리)
        squeeze_prev = self.dataFrame['squeeze_on'].shift(1)
        squeeze_curr = self.dataFrame['squeeze_on']
        
        self.dataFrame['squeeze_start'] = False  # 기본값
        self.dataFrame['squeeze_end'] = False    # 기본값
        
        # 유효한 데이터만 처리
        valid_squeeze = pd.notna(squeeze_prev) & pd.notna(squeeze_curr)
        
        self.dataFrame.loc[valid_squeeze, 'squeeze_start'] = (
            (~squeeze_prev.loc[valid_squeeze]) & 
            (squeeze_curr.loc[valid_squeeze])
        )
        
        self.dataFrame.loc[valid_squeeze, 'squeeze_end'] = (
            (squeeze_prev.loc[valid_squeeze]) & 
            (~squeeze_curr.loc[valid_squeeze])
        )
        
        # Momentum 방향 변화 (NaN 값 안전 처리)
        self.dataFrame['momentum_prev'] = self.dataFrame['momentum'].shift(1)
        
        momentum_curr = self.dataFrame['momentum']
        momentum_prev = self.dataFrame['momentum_prev']
        valid_momentum = pd.notna(momentum_curr) & pd.notna(momentum_prev)
        
        self.dataFrame['momentum_increasing'] = False  # 기본값
        self.dataFrame['momentum_decreasing'] = False  # 기본값
        
        self.dataFrame.loc[valid_momentum, 'momentum_increasing'] = (
            momentum_curr.loc[valid_momentum] > momentum_prev.loc[valid_momentum]
        )
        self.dataFrame.loc[valid_momentum, 'momentum_decreasing'] = (
            momentum_curr.loc[valid_momentum] < momentum_prev.loc[valid_momentum]
        )
        
        # Momentum이 0선을 교차 (NaN 값 안전 처리)
        self.dataFrame['momentum_cross_up'] = False    # 기본값
        self.dataFrame['momentum_cross_down'] = False  # 기본값
        
        self.dataFrame.loc[valid_momentum, 'momentum_cross_up'] = (
            (momentum_prev.loc[valid_momentum] <= 0) & 
            (momentum_curr.loc[valid_momentum] > 0)
        )
        
        self.dataFrame.loc[valid_momentum, 'momentum_cross_down'] = (
            (momentum_prev.loc[valid_momentum] >= 0) & 
            (momentum_curr.loc[valid_momentum] < 0)
        )
        
        # 이동평균 정렬
        self.dataFrame['ma_uptrend'] = self.dataFrame['MA20'] > self.dataFrame['MA50']
        self.dataFrame['ma_downtrend'] = self.dataFrame['MA20'] < self.dataFrame['MA50']
        
        # Price position relative to Bollinger Bands
        self.dataFrame['bb_squeeze_ratio'] = (
            (self.dataFrame['close'] - self.dataFrame['BB_lower']) / 
            (self.dataFrame['BB_upper'] - self.dataFrame['BB_lower'])
        )

    def get_dataframe(self):
        """현재 데이터프레임 반환"""
        if self.dataFrame is None:
            raise ValueError("DataFrame is not set. Please set the DataFrame using set_data() method.")
        return self.dataFrame

    def run(self, target_time=None) -> TradingSignal:
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
        latest = filtered_data.iloc[0]
        current_price = latest['close']
        
        # 각종 신호 확인 (NaN 값을 False로 처리)
        squeeze_on = bool(latest['squeeze_on']) if pd.notna(latest['squeeze_on']) else False
        squeeze_start = bool(latest['squeeze_start']) if pd.notna(latest['squeeze_start']) else False
        squeeze_end = bool(latest['squeeze_end']) if pd.notna(latest['squeeze_end']) else False
        momentum = latest['momentum'] if pd.notna(latest['momentum']) else 0.0
        momentum_increasing = bool(latest['momentum_increasing']) if pd.notna(latest['momentum_increasing']) else False
        momentum_decreasing = bool(latest['momentum_decreasing']) if pd.notna(latest['momentum_decreasing']) else False
        momentum_cross_up = bool(latest['momentum_cross_up']) if pd.notna(latest['momentum_cross_up']) else False
        momentum_cross_down = bool(latest['momentum_cross_down']) if pd.notna(latest['momentum_cross_down']) else False
        ma_uptrend = bool(latest['ma_uptrend']) if pd.notna(latest['ma_uptrend']) else False
        ma_downtrend = bool(latest['ma_downtrend']) if pd.notna(latest['ma_downtrend']) else False
        bb_squeeze_ratio = latest['bb_squeeze_ratio'] if pd.notna(latest['bb_squeeze_ratio']) else 0.5
        
        # 신호 강도 계산
        buy_score = 0
        sell_score = 0
        confidence = 0.5
        position_size = 0.0
        
        # === 매수 신호 점수 계산 ===
        
        # Squeeze 종료 후 상승 momentum (가장 강력한 신호)
        if squeeze_end and momentum > 0 and momentum_increasing:    # ** 중요
            buy_score += 50
        
        # Squeeze 중이면서 momentum이 증가하고 있을 때
        if squeeze_on and momentum_increasing and momentum > 0:
            buy_score += 25
        
        # 상승 추세 중 momentum 증가
        if ma_uptrend and momentum_increasing and momentum > 0:
            buy_score += 20
        
        # === 매도 신호 점수 계산 ===
        
        # Squeeze 종료 후 하락 momentum (가장 강력한 신호)
        if squeeze_end and momentum < 0 and momentum_decreasing:
            sell_score += 50
        
        # Momentum이 0선을 하향 돌파
        if momentum_cross_down:
            sell_score += 30
        
        # Squeeze 중이면서 momentum이 감소하고 있을 때
        if squeeze_on and momentum_decreasing and momentum < 0:
            sell_score += 25
        
        # 하락 추세 중 momentum 감소
        if ma_downtrend and momentum_decreasing and momentum < 0:
            sell_score += 20
        
        # === 신호 결정 로직 ===
        if buy_score >= 60:  # 매우 강력한 매수 신호
            confidence = min(0.95, 0.7 + (buy_score - 60) * 0.01)
            position_size = min(1.0, (buy_score - 40) * 0.015)
            
            return TradingSignal.create_buy_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=position_size,
                confidence=confidence
            )
        
        elif sell_score >= 60:  # 매우 강력한 매도 신호
            confidence = min(0.95, 0.7 + (sell_score - 60) * 0.01)
            position_size = min(1.0, (sell_score - 40) * 0.015)
            
            return TradingSignal.create_sell_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=position_size,
                confidence=confidence
            )
        
        elif buy_score >= 35:  # 중간 강도 매수 신호
            confidence = 0.65
            position_size = 0.4
            
            return TradingSignal.create_buy_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=position_size,
                confidence=confidence
            )
        
        elif sell_score >= 35:  # 중간 강도 매도 신호
            confidence = 0.65
            position_size = 0.4
            
            return TradingSignal.create_sell_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=position_size,
                confidence=confidence
            )
        
        elif buy_score >= 20:  # 약한 매수 신호
            confidence = 0.55
            position_size = 0.2
            
            return TradingSignal.create_buy_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=position_size,
                confidence=confidence
            )
        
        elif sell_score >= 20:  # 약한 매도 신호
            confidence = 0.55
            position_size = 0.2
            
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
