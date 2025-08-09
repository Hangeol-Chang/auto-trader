"""
Pine Script 스타일의 전략 구현
TradingView Pine Script와 유사한 문법을 Python으로 구현
"""

import pandas as pd
import numpy as np
from typing import Union, Optional, List
from datetime import datetime
from .strategy import Strategy, TradingSignal, SignalType

class PineStyleStrategy(Strategy):
    """Pine Script 스타일의 전략 베이스 클래스"""
    
    def __init__(self):
        super().__init__()
        self.length = 14  # 기본 기간
        self.source = "close"  # 기본 소스
        
    def ta_sma(self, source: pd.Series, length: int) -> pd.Series:
        """Simple Moving Average - Pine Script의 ta.sma() 구현"""
        return source.rolling(window=length).mean()
    
    def ta_ema(self, source: pd.Series, length: int) -> pd.Series:
        """Exponential Moving Average - Pine Script의 ta.ema() 구현"""
        return source.ewm(span=length).mean()
    
    def ta_rsi(self, source: pd.Series, length: int = 14) -> pd.Series:
        """Relative Strength Index - Pine Script의 ta.rsi() 구현"""
        delta = source.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def ta_macd(self, source: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """MACD - Pine Script의 ta.macd() 구현"""
        ema_fast = self.ta_ema(source, fast)
        ema_slow = self.ta_ema(source, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self.ta_ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def ta_bb(self, source: pd.Series, length: int = 20, mult: float = 2.0):
        """Bollinger Bands - Pine Script의 ta.bb() 구현"""
        basis = self.ta_sma(source, length)
        dev = mult * source.rolling(window=length).std()
        upper = basis + dev
        lower = basis - dev
        return upper, basis, lower
    
    def ta_stoch(self, high: pd.Series, low: pd.Series, close: pd.Series, k: int = 14, d: int = 3):
        """Stochastic - Pine Script의 ta.stoch() 구현"""
        lowest_low = low.rolling(window=k).min()
        highest_high = high.rolling(window=k).max()
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d).mean()
        return k_percent, d_percent
    
    def crossover(self, a: pd.Series, b: pd.Series) -> pd.Series:
        """Cross Over - Pine Script의 ta.crossover() 구현"""
        return (a > b) & (a.shift(1) <= b.shift(1))
    
    def crossunder(self, a: pd.Series, b: pd.Series) -> pd.Series:
        """Cross Under - Pine Script의 ta.crossunder() 구현"""
        return (a < b) & (a.shift(1) >= b.shift(1))
    
    def highest(self, source: pd.Series, length: int) -> pd.Series:
        """Highest - Pine Script의 ta.highest() 구현"""
        return source.rolling(window=length).max()
    
    def lowest(self, source: pd.Series, length: int) -> pd.Series:
        """Lowest - Pine Script의 ta.lowest() 구현"""
        return source.rolling(window=length).min()

class ExamplePineStrategy(PineStyleStrategy):
    """Pine Script 스타일 예제 전략"""
    
    def __init__(self):
        super().__init__()
        self.strategy_name = "Pine Style RSI + MA"
        
        # Pine Script 스타일 매개변수
        self.rsi_length = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.ma_length = 50
    
    def run(self, ticker: str, target_time: str, data: pd.DataFrame) -> TradingSignal:
        """Pine Script 스타일로 전략 실행"""
        
        if data is None or data.empty or len(data) < max(self.rsi_length, self.ma_length):
            return TradingSignal.create_hold_signal(ticker, target_time, 0)
        
        # Pine Script 스타일 지표 계산
        close = data['Close']
        
        # RSI 계산
        rsi = self.ta_rsi(close, self.rsi_length)
        
        # Moving Average 계산
        ma = self.ta_sma(close, self.ma_length)
        
        # 현재 값들
        current_rsi = rsi.iloc[-1]
        current_price = close.iloc[-1]
        current_ma = ma.iloc[-1]
        
        # Pine Script 스타일 조건문
        long_condition = (current_rsi < self.rsi_oversold) and (current_price > current_ma)
        short_condition = (current_rsi > self.rsi_overbought) and (current_price < current_ma)
        
        # 신호 생성
        if long_condition:
            return TradingSignal(
                timestamp=datetime.now(),
                signal_type=SignalType.BUY,
                target_time=target_time,
                ticker=ticker,
                current_price=int(current_price),
                position_size=1.0,
                confidence=0.8
            )
        elif short_condition:
            return TradingSignal(
                timestamp=datetime.now(),
                signal_type=SignalType.SELL,
                target_time=target_time,
                ticker=ticker,
                current_price=int(current_price),
                position_size=1.0,
                confidence=0.8
            )
        else:
            return TradingSignal.create_hold_signal(ticker, target_time, int(current_price))

class PineScriptMACD(PineStyleStrategy):
    """Pine Script MACD 전략 예제"""
    
    def __init__(self):
        super().__init__()
        self.strategy_name = "Pine MACD Strategy"
        
    def run(self, ticker: str, target_time: str, data: pd.DataFrame) -> TradingSignal:
        """MACD 기반 Pine Script 스타일 전략"""
        
        if data is None or data.empty or len(data) < 26:
            return TradingSignal.create_hold_signal(ticker, target_time, 0)
        
        close = data['Close']
        
        # MACD 계산
        macd_line, signal_line, histogram = self.ta_macd(close)
        
        # 크로스오버 조건
        macd_crossover = self.crossover(macd_line, signal_line)
        macd_crossunder = self.crossunder(macd_line, signal_line)
        
        current_price = close.iloc[-1]
        
        # 최근 크로스오버 확인
        if macd_crossover.iloc[-1]:
            return TradingSignal(
                timestamp=datetime.now(),
                signal_type=SignalType.BUY,
                target_time=target_time,
                ticker=ticker,
                current_price=int(current_price),
                position_size=1.0,
                confidence=0.75
            )
        elif macd_crossunder.iloc[-1]:
            return TradingSignal(
                timestamp=datetime.now(),
                signal_type=SignalType.SELL,
                target_time=target_time,
                ticker=ticker,
                current_price=int(current_price),
                position_size=1.0,
                confidence=0.75
            )
        else:
            return TradingSignal.create_hold_signal(ticker, target_time, int(current_price))
