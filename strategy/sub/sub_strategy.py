from turtle import pd
from strategy.strategy import SignalType, TradingSignal

class Sub_Strategy():
    def __init__(self):
        pass

    def set_data(self, ticker, dataFrame=None):
        raise NotImplementedError("Sub_Strategy must implement set_data method")

    # 메인에서 결정된 시그널을 받아서 보수적으로 어떻게 할지 정하는 로직.
    def run(self, target_time=None, signal : TradingSignal = None) -> TradingSignal:
        raise NotImplementedError("Sub_Strategy must implement run method")