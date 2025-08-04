import multiprocessing
import time
import logging

from core import visualizer, trader
from module import stock_data_manager as sd_m
from module import stock_data_manager_ws as sd_m_ws
from module import token_manager as tm

# INVEST_TYPE = "PROD"  # 실전투자
INVEST_TYPE = "VPS"    # 모의투자

if __name__ == "__main__":
    # token_manager.auth_validate(invest_type=INVEST_TYPE)
    tm.auth_ws_validate(invest_type=INVEST_TYPE)

    print("init")
    kws = tm.KISWebSocket(api_url="/tryitout")
    print("init done")
    kws.subscribe(request=sd_m_ws.asking_price_krx, data=["005930", "000660"])
    print("subscribed")
    
    def on_result(ws, tr_id, result, data_info):
        print("result:", result)
        print("data_info:", data_info)

    # 장 마감 시간에는 데이터 안들어옴...
    kws.start(on_result=on_result)