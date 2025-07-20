import time
import eel

import argparse
import json
import logging

from module import token_manager
from module import stock_data_manager
from quantylab import utils

# INVEST_TYPE = "PROD"  # 실전투자
INVEST_TYPE = "VPS"    # 모의투자

'''
    # rltrader 기본 실행.
    python main.py
    --mode train --ver v3 --name 005930 --stock_code 005930
    --rl_method dqn --start_date 20180101 --end_date 20191230
'''

'''
    # args desription
    --mode: 
        - train : 학습 모드
        - test : 테스트 모드
        - update : 모델 업데이트 모드
        - predict : 예측 모드

    --name: 실행 이름
    --stock_code: 종목 코드 (예: 005930) -> 추후에는 이것조차 자동으로 하도록

    --rl_method: 
        - dqn
        - pg
        - ac
        - a2c
        - a3c
        - monkey

    --net: 
        - dnn
        - lstm
        - cnn
        - monkey

    --backend: 
        - pytorch
        - tensorflow
        - plaidml

    --start_date: 시작 날짜 (예: 20200101)
    --end_date: 종료 날짜 (예: 20201231)
    --lr: 학습률 (예: 0.0001)
    --discount_factor: 할인율 (예: 0.7)
'''

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['train', 'test', 'update', 'predict'], default='train')
    parser.add_argument('--name', default=utils.get_time_str())
    parser.add_argument('--stock_code', nargs='+')
    parser.add_argument('--rl_method', choices=['dqn', 'pg', 'ac', 'a2c', 'a3c', 'monkey'])
    parser.add_argument('--net', choices=['dnn', 'lstm', 'cnn', 'monkey'], default='dnn')
    parser.add_argument('--backend', choices=['pytorch', 'tensorflow', 'plaidml'], default='pytorch')
    parser.add_argument('--start_date', default='20200101')
    parser.add_argument('--end_date', default='20201231')
    parser.add_argument('--lr', type=float, default=0.0001)
    parser.add_argument('--discount_factor', type=float, default=0.7)
    parser.add_argument('--balance', type=int, default=100000000)

    # keys = token_manager.get_keys()

    # '''
    test_data = stock_data_manager.get_itempricechart_1(
        div_code="J", itm_no="005930",  # 삼성전자
        start_date=20250701, end_date=20250715, period_code="D", adj_prc="1",
    )
    print(test_data, "\n\n----\n\n")

    test_data = stock_data_manager.get_itempricechart_2(
        div_code="J", itm_no="005930",  # 삼성전자
        start_date=20240101, period_code="D", adj_prc="1"
    )
    print(test_data, "\n\n----\n\n")
    time.sleep(1)
    test_data = stock_data_manager.get_daily_price(
        div_code="J", itm_no="005930",  # 삼성전자
        period_code="D", adj_prc_code="1",
    )
    print(test_data, "\n\n----\n\n")
    # '''
    
    # eel.init("web")
    # eel.start("web/index.html", size=(800, 600))