
"""
    자동 트레이딩 모듈

    부착될 모듈들
    - strategy : 매수, 매매 타이밍을 잡아오는 모듈
    - orderer : 실제 주문을 실행하는 모듈.
"""

import logging
import pandas as pd
from module import stock_data_manager
from module import stock_orderer
from strategy.strategy import SignalType
from strategy import    \
    ma_strategy, \
    macd_strategy, \
    squeeze_momentum_strategy, \
    rsi_strategy

from strategy.sub import \
    stop_loss_strategy

STATE_DATA_DIR = "data/state"

logger = logging.getLogger(__name__)


STRATEGIES = {
    "MA":               ma_strategy.MA_strategy,
    "MACD":             macd_strategy.MACD_strategy,
    "SqueezeMomentum":  squeeze_momentum_strategy.SqueezeMomentum_strategy,
    "RSI":              rsi_strategy.RSI_strategy,
    # 다른 전략들을 여기에 추가할 수 있습니다.
}

SUB_STRATEGIES = {
    "StopLoss":        stop_loss_strategy.StopLoss_strategy,
}

class Trader:
    '''
        호출 순서 : 
            1. set_strategy() 
            2. set_data() 
            3. run_backtest() or run_trader()
    '''
    def __init__(self, type=""):
        self.type = type
        self.strategy = None
        
        if type == "backtest":
            self.orderer = stock_orderer.BackTest_Orderer()
        elif type == "paper":
            self.orderer = stock_orderer.Paper_Orderer()
        elif type == "live":
            self.orderer = stock_orderer.Live_Orderer()

    def set_strategy(self, strategy_name):
        """전략 설정"""
        if strategy_name in STRATEGIES:
            self.strategy = STRATEGIES[strategy_name]()
            print(f"Strategy set to {strategy_name} || {self.strategy.name}")
            logger.info(f"Strategy set to {strategy_name}")
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
    def add_sub_strategy(self, sub_strategy_name):
        """서브 전략 추가"""
        if self.strategy is None:
            raise ValueError("Main strategy is not set. Please set the main strategy first.")
        
        if sub_strategy_name in STRATEGIES:
            sub_strategy = STRATEGIES[sub_strategy_name]()
            self.strategy.add_sub_strategy(sub_strategy)
            print(f"Sub strategy {sub_strategy_name} added")
            logger.info(f"Sub strategy {sub_strategy_name} added")
        else:
            raise ValueError(f"Unknown sub strategy: {sub_strategy_name}")


    def set_data(self, ticker, start_date, end_date):
        start_date = stock_data_manager.get_offset_date(start_date, -60)  # 60일 전부터 데이터를 가져오기

        # start_date부터 end_date까지를
        print(f"{start_date} ~ {end_date} 기간의 데이터를 가져옵니다.")
        dataFrame = stock_data_manager.get_itempricechart_2(
            ticker=ticker,
            start_date=start_date, end_date=end_date
        )
        data = self.strategy.set_data(ticker, dataFrame)
        print(f"Data for {ticker} set with {len(self.strategy.dataFrame)} records")
        
        return data.to_json(orient='records')

    def run_backtest(self, ticker, start_date, end_date):
        print("\n============= Backtest Start =============")
        print(f"Running backtest for {ticker} from {start_date} to {end_date}...")
        country_code = stock_data_manager.get_country_code(ticker)

        now = stock_data_manager.get_next_trading_day(start_date, country_code=country_code)

        # trade_info = pd.DataFrame()
        while now <= end_date:
            try:
                res = self.strategy.run(target_time=now)    # 전략에 따른 판단.
                self.orderer.place_order(order_info=res)    # 거래 수행

            except Exception as e:
                # 날짜가 없는 에러가 종종 남
                print(f"[오류] {e}")

            now = stock_data_manager.get_offset_date(now, 1)  # 다음 거래일로 이동
            now = stock_data_manager.get_next_trading_day(now, country_code=country_code)


        # print(trade_info)
        trade_result = self.orderer.end_test()

        print("============= Backtest End =============\n")
        return trade_result

    def run_trader(self):
        print("Running trader...")
        pass