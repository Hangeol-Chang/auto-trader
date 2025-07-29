from dataclasses import dataclass
import pandas as pd
from strategy.strategy import *

class MACD_strategy(STRATEGY):
    def __init__(self, period: int = 20, std_multiplier: float = 2.0):
        super().__init__()
        self.name = "Multi-MA + MACD Strategy"  # 전략 이름 변경
        self.period = period                # 이동평균 기간 (사용하지 않음)
        self.std_multiplier = std_multiplier # 표준편차 배수 (사용하지 않음)
        self.dataFrame = None
        self.position_size = 0.0            # 현재 포지션 크기 추가

    def set_data(self, ticker, dataFrame):
        self.ticker = ticker
        self.dataFrame = dataFrame
        self.dataFrame['date'] = pd.to_datetime(self.dataFrame['date'], format='%Y%m%d', errors='coerce')
        self.calculate_moving_averages()
        return self.dataFrame

    def calculate_moving_averages(self):                
        # MA5, MA20, MA60 계산
        self.dataFrame['MA5'] = self.dataFrame['close'].rolling(window=5).mean()
        self.dataFrame['MA20'] = self.dataFrame['close'].rolling(window=20).mean()
        self.dataFrame['MA60'] = self.dataFrame['close'].rolling(window=60).mean()
        
        # MACD 계산 (12, 26, 9)
        exp1 = self.dataFrame['close'].ewm(span=12).mean()
        exp2 = self.dataFrame['close'].ewm(span=26).mean()
        self.dataFrame['MACD'] = exp1 - exp2
        self.dataFrame['MACD_signal'] = self.dataFrame['MACD'].ewm(span=9).mean()
        self.dataFrame['MACD_histogram'] = self.dataFrame['MACD'] - self.dataFrame['MACD_signal']
        
        # 전일 값들
        self.dataFrame['MA5_prev'] = self.dataFrame['MA5'].shift(1)
        self.dataFrame['MA20_prev'] = self.dataFrame['MA20'].shift(1)
        self.dataFrame['MA60_prev'] = self.dataFrame['MA60'].shift(1)
        self.dataFrame['MACD_prev'] = self.dataFrame['MACD'].shift(1)
        self.dataFrame['MACD_signal_prev'] = self.dataFrame['MACD_signal'].shift(1)
        
        # 이동평균 정렬 확인 (상승 추세: MA5 > MA20)
        self.dataFrame['uptrend'] = (self.dataFrame['MA5'] > self.dataFrame['MA20'])
        
        # 이동평균 정렬 확인 (하락 추세: MA5 < MA20)
        self.dataFrame['downtrend'] = (self.dataFrame['MA5'] < self.dataFrame['MA20'])
        
        # 골든 크로스: MA5가 MA20을 상향 돌파
        self.dataFrame['golden_cross'] = (
            (self.dataFrame['MA5_prev'] <= self.dataFrame['MA20_prev']) & 
            (self.dataFrame['MA5'] > self.dataFrame['MA20'])
        )
        
        # 데드 크로스: MA5가 MA20을 하향 돌파
        self.dataFrame['dead_cross'] = (
            (self.dataFrame['MA5_prev'] >= self.dataFrame['MA20_prev']) & 
            (self.dataFrame['MA5'] < self.dataFrame['MA20'])
        )

        
        # MACD 골든 크로스: MACD가 Signal을 상향 돌파
        self.dataFrame['macd_golden_cross'] = (
            (self.dataFrame['MACD_prev'] <= self.dataFrame['MACD_signal_prev']) & 
            (self.dataFrame['MACD'] > self.dataFrame['MACD_signal'])
        )
        
        # MACD 데드 크로스: MACD가 Signal을 하향 돌파
        self.dataFrame['macd_dead_cross'] = (
            (self.dataFrame['MACD_prev'] >= self.dataFrame['MACD_signal_prev']) & 
            (self.dataFrame['MACD'] < self.dataFrame['MACD_signal'])
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
        
        # 각종 신호 확인
        golden_cross = latest['golden_cross']
        dead_cross = latest['dead_cross']
        macd_golden_cross = latest['macd_golden_cross']
        macd_dead_cross = latest['macd_dead_cross']
        uptrend = latest['uptrend']
        downtrend = latest['downtrend']
        
        ma5 = latest['MA5']
        ma20 = latest['MA20']
        ma60 = latest['MA60']
        macd = latest['MACD']
        macd_signal = latest['MACD_signal']
        macd_histogram = latest['MACD_histogram']
        
        # 신호 강도 계산
        buy_score = 0
        sell_score = 0
        confidence = 0.5
        position_size = 0.0
        
        # === 매수 신호 점수 계산 ===
        if golden_cross:  # MA5-MA20 골든 크로스 (강력한 매수 신호)
            buy_score += 50
        
        if macd_golden_cross and macd < 0:  # MACD 골든 크로스 (특히 0선 아래에서)
            buy_score += 30
        
        if uptrend and macd_histogram > 0:  # 상승 추세 + MACD 히스토그램 양수
            buy_score += 25
        
        if ma5 > ma20 and macd > macd_signal:  # 상승 배열 + MACD 신호
            buy_score += 20
        
        # === 매도 신호 점수 계산 ===
        if dead_cross:  # MA5-MA20 데드 크로스 (강력한 매도 신호)
            sell_score += 50
        
        if macd_dead_cross and macd > 0:  # MACD 데드 크로스 (특히 0선 위에서)
            sell_score += 30
        
        if downtrend and macd_histogram < 0:  # 하락 추세 + MACD 히스토그램 음수
            sell_score += 25
        
        if ma5 < ma20 and macd < macd_signal:  # 하락 배열 + MACD 신호
            sell_score += 20
        
        # === 신호 결정 로직 ===
        # 포지션 관리: 매수는 position_size < 1.0일 때만, 매도는 position_size > 0.0일 때만
        
        if buy_score >= 50 and self.position_size < 1.0:  # 강력한 매수 신호
            confidence = min(0.9, 0.6 + (buy_score - 50) * 0.01)
            trade_position_size = min(1.0 - self.position_size, 0.5)  # 강한 신호: 0.5
            
            # 포지션 크기 업데이트
            self.position_size += trade_position_size
            
            return TradingSignal.create_buy_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=trade_position_size,
                confidence=confidence
            )
        
        elif sell_score >= 50 and self.position_size > 0.0:  # 강력한 매도 신호
            confidence = min(0.9, 0.6 + (sell_score - 50) * 0.01)
            trade_position_size = min(self.position_size, 1.0)  # 강한 신호: 전량 매도 (1.0)
            
            # 포지션 크기 업데이트
            self.position_size -= trade_position_size
            
            return TradingSignal.create_sell_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=trade_position_size,
                confidence=confidence
            )
        
        elif buy_score >= 30 and self.position_size < 1.0:  # 약한 매수 신호
            confidence = 0.6
            trade_position_size = min(1.0 - self.position_size, 0.3)  # 약한 신호: 0.3
            
            # 포지션 크기 업데이트
            self.position_size += trade_position_size
            
            return TradingSignal.create_buy_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=trade_position_size,
                confidence=confidence
            )
        
        elif sell_score >= 30 and self.position_size > 0.0:  # 약한 매도 신호
            confidence = 0.6
            trade_position_size = min(self.position_size, 0.5)  # 약한 신호: 0.5
            
            # 포지션 크기 업데이트
            self.position_size -= trade_position_size
            
            return TradingSignal.create_sell_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=trade_position_size,
                confidence=confidence
            )
        
        else:  # 신호 없음 (홀드) 또는 포지션 한계에 도달
            return TradingSignal.create_hold_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price
            )