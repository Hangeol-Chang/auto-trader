



from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime

class SignalType(Enum):
    """매매 신호 타입"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class PositionSize(Enum):
    """포지션 크기"""
    SMALL = 0.25    # 25%
    MEDIUM = 0.5    # 50%
    LARGE = 0.75    # 75%
    FULL = 1.0      # 100%

@dataclass
class TradingSignal:
    """매매 신호 구조체"""
    
    # 기본 신호 정보
    signal_type: SignalType                    # 매수/매도/홀드
    timestamp: datetime                        # 신호 발생 시간
    ticker: str                               # 종목 코드
    current_price: float                      # 현재 가격
    
    # 포지션 정보
    position_size: float                      # 매수/매도 비율 (0.0 ~ 1.0)
    quantity: Optional[int] = None            # 매수/매도 수량 (주)
    target_amount: Optional[float] = None     # 목표 매수/매도 금액
    
    # 가격 정보
    entry_price: Optional[float] = None       # 진입 가격
    stop_loss: Optional[float] = None         # 손절가
    take_profit: Optional[float] = None       # 익절가
    
    # 전략 정보
    strategy_name: str = ""                   # 전략 이름
    confidence: float = 0.0                   # 신호 신뢰도 (0.0 ~ 1.0)
    reason: str = ""                          # 매매 이유/근거
    
    # 기술적 지표 정보
    technical_data: Dict[str, Any] = None     # 기술적 지표 데이터
    
    # 리스크 관리
    risk_level: str = "MEDIUM"                # LOW, MEDIUM, HIGH
    max_loss_percent: float = 5.0             # 최대 손실 허용 비율 (%)
    
    def __post_init__(self):
        """초기화 후 처리"""
        if self.technical_data is None:
            self.technical_data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'signal_type': self.signal_type.value,
            'timestamp': self.timestamp.isoformat(),
            'ticker': self.ticker,
            'current_price': self.current_price,
            'position_size': self.position_size,
            'quantity': self.quantity,
            'target_amount': self.target_amount,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'strategy_name': self.strategy_name,
            'confidence': self.confidence,
            'reason': self.reason,
            'technical_data': self.technical_data,
            'risk_level': self.risk_level,
            'max_loss_percent': self.max_loss_percent
        }
    
    @classmethod
    def create_hold_signal(cls, ticker: str, current_price: float, strategy_name: str = ""):
        """홀드 신호 생성 헬퍼 메소드"""
        return cls(
            signal_type=SignalType.HOLD,
            timestamp=datetime.now(),
            ticker=ticker,
            current_price=current_price,
            position_size=0.0,
            strategy_name=strategy_name,
            reason="No clear signal"
        )
    
    @classmethod
    def create_buy_signal(cls, ticker: str, current_price: float, position_size: float, 
                         strategy_name: str = "", reason: str = "", confidence: float = 0.5):
        """매수 신호 생성 헬퍼 메소드"""
        return cls(
            signal_type=SignalType.BUY,
            timestamp=datetime.now(),
            ticker=ticker,
            current_price=current_price,
            position_size=position_size,
            entry_price=current_price,
            strategy_name=strategy_name,
            reason=reason,
            confidence=confidence
        )
    
    @classmethod
    def create_sell_signal(cls, ticker: str, current_price: float, position_size: float,
                          strategy_name: str = "", reason: str = "", confidence: float = 0.5):
        """매도 신호 생성 헬퍼 메소드"""
        return cls(
            signal_type=SignalType.SELL,
            timestamp=datetime.now(),
            ticker=ticker,
            current_price=current_price,
            position_size=position_size,
            strategy_name=strategy_name,
            reason=reason,
            confidence=confidence
        )

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

    def set_date(self, dataFrame):
        self.dataFrame = dataFrame
        self.calculate_bollinger_bands()

    def calculate_bollinger_bands(self):
        """볼린저 밴드 계산"""
        import pandas as pd
        
        # 이동평균 계산
        self.dataFrame['MA'] = self.dataFrame['close'].rolling(window=self.period).mean()

        # 표준편차 계산
        self.dataFrame['STD'] = self.dataFrame['close'].rolling(window=self.period).std()

        # 상단/하단 밴드 계산
        self.dataFrame['upper_band'] = self.dataFrame['MA'] + (self.dataFrame['STD'] * self.std_multiplier)
        self.dataFrame['lower_band'] = self.dataFrame['MA'] - (self.dataFrame['STD'] * self.std_multiplier)

        # %B 계산 (현재가가 밴드 내에서 차지하는 위치)
        self.dataFrame['percent_b'] = (self.dataFrame['close'] - self.dataFrame['lower_band']) / (self.dataFrame['upper_band'] - self.dataFrame['lower_band'])

        return self.dataFrame

    def run(self, targetTime=None) -> TradingSignal:
        if targetTime is None:
            raise ValueError("targetTime must be provided")
        if self.dataFrame is None:
            raise ValueError("dataFrame must be set before running the strategy")
        
        # 최신 데이터 가져오기
        # targetTime 이전까지의 데이터를 가져오기.
        latest = self.dataFrame
        ticker = getattr(latest, 'ticker', 'Unknown')
        current_price = latest['close']
        percent_b = latest['percent_b']
        
        # 기술적 데이터 준비
        technical_data = {
            'upper_band': latest['upper_band'],
            'lower_band': latest['lower_band'],
            'middle_band': latest['MA'],
            'percent_b': percent_b,
            'std': latest['STD']
        }
        
        # 매매 신호 결정
        if percent_b <= 0.0:  # 하단 밴드 터치 또는 돌파 (과매도)
            return TradingSignal.create_buy_signal(
                ticker=ticker,
                current_price=current_price,
                position_size=0.5,  # 50% 매수
                strategy_name=self.name,
                reason=f"Price touched lower band (% = {percent_b:.3f})",
                confidence=0.8
            )
        
        elif percent_b >= 1.0:  # 상단 밴드 터치 또는 돌파 (과매수)
            return TradingSignal.create_sell_signal(
                ticker=ticker,
                current_price=current_price,
                position_size=0.5,  # 50% 매도
                strategy_name=self.name,
                reason=f"Price touched upper band (%B = {percent_b:.3f})",
                confidence=0.8
            )
        
        elif percent_b <= 0.2:  # 하단 근처 (약한 매수 신호)
            return TradingSignal.create_buy_signal(
                ticker=ticker,
                current_price=current_price,
                position_size=0.25,  # 25% 매수
                strategy_name=self.name,
                reason=f"Price near lower band (%B = {percent_b:.3f})",
                confidence=0.6
            )
        
        elif percent_b >= 0.8:  # 상단 근처 (약한 매도 신호)
            return TradingSignal.create_sell_signal(
                ticker=ticker,
                current_price=current_price,
                position_size=0.25,  # 25% 매도
                strategy_name=self.name,
                reason=f"Price near upper band (%B = {percent_b:.3f})",
                confidence=0.6
            )
        
        else:  # 중립 구간 (홀드)
            signal = TradingSignal.create_hold_signal(ticker, current_price, self.name)
            signal.reason = f"Price in neutral zone (%B = {percent_b:.3f})"
            signal.technical_data = technical_data
            return signal