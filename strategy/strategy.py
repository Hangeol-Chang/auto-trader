from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime

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

    def set_data(self, ticker, dataFrame=None, state=None):
        """
        데이터 설정 메소드
        :param ticker: 종목 코드
        :param dataFrame: 데이터프레임 (주가 데이터 등)
        :param state: 현재 상태 (예: 포트폴리오, 잔고 등)
        :return: 데이터프레임
        """
        raise NotImplementedError("set_data 메소드를 구현해야 합니다.")
    
    def get_dataframe(self):
        """
        현재 데이터프레임 반환 메소드
        :return: 현재 데이터프레임
        """
        if self.dataFrame is None:
            raise ValueError("DataFrame is not set. Please set the DataFrame using set_data() method.")
        return self.dataFrame

    def run(self, target_time=None, state=None) -> TradingSignal:
        """
        전략 실행 메소드
        :param target_time: 전략을 실행할 날짜 (예: '2023-01-01')
        :param state: 현재 상태 (예: 포트폴리오, 잔고 등) -> stock_orderer 참고
        :return: TradingSignal 객체
        """
        raise NotImplementedError("run 메소드를 구현해야 합니다.")