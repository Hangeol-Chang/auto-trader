
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
from datetime import datetime, timedelta
from module import stock_data_manager

STATE_DATA_DIR = "data/state"

logger = logging.getLogger(__name__)

class Trader:
    
    def __init__(self, type=""):
        pass

    def run_backtest(self, ticker, start_date, end_date):
        print("\n============= Backtest Start =============")
        print(f"Running backtest for {ticker} from {start_date} to {end_date}...")

        # ticker의 

        # start_date부터 end_date까지를 
        stock_data_manager.



        print("============= Backtest End =============\n")
        pass

    def run_trader(self):
        print("Running trader...")
        pass