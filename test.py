import multiprocessing
import time
import logging

from core import visualizer, trader
from module import stock_data_manager, token_manager

# INVEST_TYPE = "PROD"  # 실전투자
INVEST_TYPE = "VPS"    # 모의투자

if __name__ == "__main__":
    token_manager.auth_validate(invest_type=INVEST_TYPE)
    token_manager.auth_ws_validate(invest_type=INVEST_TYPE)
    
    pass