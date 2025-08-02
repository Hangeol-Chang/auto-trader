from dataclasses import dataclass
import pandas as pd
from strategy.strategy import *

class MA_strategy(STRATEGY):
    def __init__(self, period: int = 20, std_multiplier: float = 2.0):
        super().__init__()
        self.name = "MA5-MA20 Golden Cross Strategy"
        self.period = period                # 이동평균 기간 (사용하지 않음)
        self.std_multiplier = std_multiplier # 표준편차 배수 (사용하지 않음)
        self.dataFrame = None
        self.position_size = 0.0            # 현재 포지션 크기

    def set_data(self, ticker, dataFrame):
        self.ticker = ticker
        self.dataFrame = dataFrame.copy()  # 원본 데이터 보호
        
        print(self.dataFrame)

        # 중복된 컬럼명 확인 및 제거
        if self.dataFrame.columns.duplicated().any():
            print("중복된 컬럼명 발견, 제거합니다.")
            # 중복된 컬럼 제거 (첫 번째 것만 유지)
            self.dataFrame = self.dataFrame.loc[:, ~self.dataFrame.columns.duplicated()]
        
        # 중복된 행 제거
        self.dataFrame = self.dataFrame.drop_duplicates().reset_index(drop=True)
        
        # 날짜 컬럼 변환 (에러 방지)
        try:
            self.dataFrame['date'] = pd.to_datetime(self.dataFrame['date'], format='%Y%m%d', errors='coerce')
        except Exception as e:
            print(f"날짜 변환 중 에러 발생: {e}")
            # 날짜가 이미 datetime 형태인 경우 그대로 사용
            if self.dataFrame['date'].dtype != 'datetime64[ns]':
                # 다른 형식으로 시도
                self.dataFrame['date'] = pd.to_datetime(self.dataFrame['date'], errors='coerce')
        
        # NaT (Not a Time) 값이 있는 행 제거
        self.dataFrame = self.dataFrame.dropna(subset=['date']).reset_index(drop=True)
        
        print(f"Data for {ticker} set with {len(self.dataFrame)} records")
        print(f"컬럼: {list(self.dataFrame.columns)}")
        
        self.calculate_moving_averages()
        return self.dataFrame

    def calculate_moving_averages(self):                
        # MA5, MA20 계산
        self.dataFrame['MA5'] = self.dataFrame['close'].rolling(window=5).mean()
        self.dataFrame['MA20'] = self.dataFrame['close'].rolling(window=20).mean()
        
        # 전일 값들
        self.dataFrame['MA5_prev'] = self.dataFrame['MA5'].shift(1)
        self.dataFrame['MA20_prev'] = self.dataFrame['MA20'].shift(1)
        
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
        uptrend = latest['uptrend']
        downtrend = latest['downtrend']
        
        ma5 = latest['MA5']
        ma20 = latest['MA20']
        
        # 신호 강도 계산
        buy_score = 0
        sell_score = 0
        confidence = 0.7
        
        # === 매수 신호 점수 계산 ===
        if golden_cross:  # MA5-MA20 골든 크로스 (강력한 매수 신호)
            buy_score += 100
        
        elif uptrend:  # 상승 추세 지속 (약한 매수 신호)
            buy_score += 30
        
        # === 매도 신호 점수 계산 ===
        if dead_cross:  # MA5-MA20 데드 크로스 (강력한 매도 신호)
            sell_score += 100
        
        elif downtrend:  # 하락 추세 지속 (약한 매도 신호)
            sell_score += 30
        
        # === 신호 결정 로직 ===
        # 포지션 관리: 매수는 position_size < 1.0일 때만, 매도는 position_size > 0.0일 때만
        
        if golden_cross and self.position_size < 1.0:  # 골든 크로스 매수 신호
            confidence = 0.8
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
        
        elif dead_cross and self.position_size > 0.0:  # 데드 크로스 매도 신호
            confidence = 0.8
            trade_position_size = min(self.position_size, 1.0)  # 강한 신호: 전량 매도
            
            # 포지션 크기 업데이트
            self.position_size -= trade_position_size
            
            return TradingSignal.create_sell_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=trade_position_size,
                confidence=confidence
            )
        
        elif uptrend and self.position_size < 1.0 and self.position_size == 0.0:  # 상승 추세에서 첫 매수
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
        
        elif downtrend and self.position_size > 0.0:  # 하락 추세에서 부분 매도
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
