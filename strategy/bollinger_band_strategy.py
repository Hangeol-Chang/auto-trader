



from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime
import pandas as pd

class SignalType(Enum):
    """매매 신호 타입"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class TradingSignal:
    """매매 신호 구조체"""
    timestamp: datetime                 # 신호 발생 시간

    # 기본 신호 정보
    signal_type: SignalType             # 매수/매도/홀드
    target_time: str                    # 구매한 날짜.
    ticker: str                         # 종목 코드
    current_price: int                  # 현재가 (종가)


    # 포지션 정보
    position_size: float                # 매수/매도 비율 (0.0 ~ 1.0)
    quantity: Optional[int] = None      # 매수/매도 수량 (주)
        
    confidence: float = 0.0             # 신호 신뢰도 (0.0 ~ 1.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'signal_type': self.signal_type.value,
            'target_time': self.target_time,
            'current_price': self.current_price,
            'ticker': self.ticker,
            'position_size': self.position_size,
            'quantity': self.quantity,
            'confidence': self.confidence
        }
    
    @classmethod
    def create_hold_signal(cls, ticker: str, target_time: str, current_price: int):
        """홀드 신호 생성 헬퍼 메소드"""
        return cls(
            timestamp=datetime.now(),
            signal_type=SignalType.HOLD,
            target_time=target_time,
            ticker=ticker,
            current_price=current_price,
            position_size=0.0,
        )
    
    @classmethod
    def create_buy_signal(cls, 
            ticker: str, target_time: str, current_price: int,
            position_size: float, confidence: float = 0.5):
        """매수 신호 생성 헬퍼 메소드"""
        return cls(
            timestamp=datetime.now(),
            signal_type=SignalType.BUY,
            target_time=target_time,
            ticker=ticker,
            current_price=current_price,
            position_size=position_size,
            confidence=confidence
        )
    
    @classmethod
    def create_sell_signal(cls,
            ticker: str, target_time: str, current_price: int,
            position_size: float, confidence: float = 0.5):
        """매도 신호 생성 헬퍼 메소드"""
        return cls(
            timestamp=datetime.now(),
            signal_type=SignalType.SELL,
            target_time=target_time,
            ticker=ticker,
            current_price=current_price,
            position_size=position_size,
            confidence=confidence
        )   


    def print(self):
        """신호 정보 출력"""
        print("-- Trading Signal: --")
        print(f"Timestamp: {self.timestamp.isoformat()}")
        print(f"Target Time: {self.target_time}")
        print(f"Signal Type: {self.signal_type.value}")
        print(f"Current Price: {self.current_price}")
        print(f"Ticker: {self.ticker}")
        print(f"Position Size: {self.position_size}")
        print(f"Quantity: {self.quantity if self.quantity is not None else 'N/A'}")
        print(f"Confidence: {self.confidence:.2f}")
        print("----------------------\n")

class STRATEGY:
    def __init__(self):
        pass

    def run(self, dataFrame=None) -> TradingSignal:
        """
        전략 실행 메소드
        :param dataFrame: 데이터프레임 (예: 주가 데이터)
        :return: TradingSignal 객체
        """
        raise NotImplementedError("run 메소드를 구현해야 합니다.")

class Strategy_BollingerBand(STRATEGY):
    def __init__(self, period: int = 20, std_multiplier: float = 2.0):
        super().__init__()
        self.name = "Bollinger Band Strategy"
        self.period = period                # 이동평균 기간
        self.std_multiplier = std_multiplier # 표준편차 배수
        self.dataFrame = None

    def set_data(self, ticker, dataFrame):
        self.ticker = ticker
        self.dataFrame = dataFrame
        self.dataFrame['date'] = pd.to_datetime(self.dataFrame['date'], format='%Y%m%d', errors='coerce')
        self.calculate_bollinger_bands()

    def calculate_bollinger_bands(self):                
        # 이동평균 계산
        self.dataFrame['MA'] = self.dataFrame['close'].rolling(window=self.period).mean()
        # 표준편차 계산
        self.dataFrame['STD'] = self.dataFrame['close'].rolling(window=self.period).std()

        # 상단/하단 밴드 계산
        self.dataFrame['upper_band'] = self.dataFrame['MA'] + (self.dataFrame['STD'] * self.std_multiplier)
        self.dataFrame['lower_band'] = self.dataFrame['MA'] - (self.dataFrame['STD'] * self.std_multiplier)

        # %B 계산 (현재가가 밴드 내에서 차지하는 위치)
        self.dataFrame['percent_b'] = (self.dataFrame['close'] - self.dataFrame['lower_band']) / (self.dataFrame['upper_band'] - self.dataFrame['lower_band'])
        # return self.dataFrame

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
        latest = filtered_data.iloc[0]  # 첫 번째 (유일한) 행
        current_price = latest['close']
        percent_b = latest['percent_b']
                
        # 매매 신호 결정
        if percent_b <= 0.0:  # 하단 밴드 터치 또는 돌파 (과매도)
            return TradingSignal.create_buy_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=0.5,  # 50% 매수
                confidence=0.8
            )
        
        elif percent_b >= 1.0:  # 상단 밴드 터치 또는 돌파 (과매수)
            return TradingSignal.create_sell_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=0.5,  # 50% 매도
                confidence=0.8
            )
        
        elif percent_b <= 0.2:  # 하단 근처 (약한 매수 신호)
            return TradingSignal.create_buy_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=0.25,  # 25% 매수
                confidence=0.6
            )
        
        elif percent_b >= 0.8:  # 상단 근처 (약한 매도 신호)
            return TradingSignal.create_sell_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price,
                position_size=0.25,  # 25% 매도
                confidence=0.6
            )
        
        else:  # 중립 구간 (홀드)
            return TradingSignal.create_hold_signal(
                ticker=self.ticker,
                target_time=target_time,
                current_price=current_price
            )