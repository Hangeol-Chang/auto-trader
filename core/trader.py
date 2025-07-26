
"""
    자동 트레이딩 모듈

    부착될 모듈들
    - 매수, 매매 타이밍을 잡아오는 모듈
    - \
"""

import os
import time
import logging
import json
import pandas as pd
from datetime import datetime, timedelta
from module import stock_data_manager
from strategy import macd_strategy

STATE_DATA_DIR = "data/state"

logger = logging.getLogger(__name__)


STRATEGIES = {
    "MACD": macd_strategy.MACD_strategy,
    # 다른 전략들을 여기에 추가할 수 있습니다.
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

    def set_strategy(self, strategy_name):
        """전략 설정"""
        if strategy_name in STRATEGIES:
            self.strategy = STRATEGIES[strategy_name]()
            logger.info(f"Strategy set to {strategy_name}")
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")


    def set_data(self, ticker, start_date, end_date):
        start_date = stock_data_manager.get_offset_date(start_date, -60)  # 60일 전부터 데이터를 가져오기

        # start_date부터 end_date까지를
        print(f"{start_date} ~ {end_date} 기간의 데이터를 가져옵니다.")
        dataFrame = stock_data_manager.get_itempricechart_2(
            itm_no=ticker,  # 삼성전자
            start_date=start_date, end_date=end_date
        )
        data = self.strategy.set_data(ticker, dataFrame)
        return data.to_json(orient='records')

    def run_backtest(self, ticker, start_date, end_date):
        print("\n============= Backtest Start =============")
        print(f"Running backtest for {ticker} from {start_date} to {end_date}...")

        # self.set_data(ticker, start_date, end_date)

        now = stock_data_manager.get_next_trading_day(start_date)

        trade_info = pd.DataFrame()
        while now <= end_date:
            res = self.strategy.run(target_time=now)
            if res.signal_type != "HOLD":
                # res.print()
                trade_info = pd.concat([trade_info, pd.DataFrame([{
                    'timestamp': res.timestamp,
                    'signal_type': res.signal_type,
                    'target_time': res.target_time,
                    'ticker': res.ticker,
                    'position_size': res.position_size,
                    'current_price': res.current_price,
                    'quantity': res.quantity
                }])], ignore_index=True)

            # 신호에 따라 매매 로직 수행
            now = stock_data_manager.get_offset_date(now, 1)  # 다음 거래일로 이동
            now = stock_data_manager.get_next_trading_day(now)

        # print(trade_info)
        print("============= Backtest End =============\n")
        return trade_info.to_json(orient='records')

    def run_trader(self):
        print("Running trader...")
        pass