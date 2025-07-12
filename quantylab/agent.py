
# Agent class
'''
- 투자 행동을 수행하고 보유 주식을 관리
'''

import numpy as np
# from quantylab import utils

class Agent:
    # 에이전트의 상태 수
    STATE_DIM = 3
    '''
        주식 보유 비율, 현재 손익, 평균 매수 대비 등락률 -> 3개의 상태를 가짐.
    '''

    # 매매 수수료 및 세금
    TRADING_CHARGE = 0.00015  # 거래 수수료 0.015%
    TRADING_TAX = 0.0025 # 거래세 0.25%

    # 행동
    ACTION_BUY = 0  # 매수
    ACTION_SELL = 1 # 매도
    ACTION_HOLD = 2 # 관망 (보유)
    # 인공 신경망에서 확률을 구할 행동들
    ACTIONS = [ACTION_BUY, ACTION_SELL, ACTION_HOLD]
    NUM_ACTIONS = len(ACTIONS) 

    def __init__(self, environment, initial_balance, min_trading_price, max_trading_price):
        # 현재 주식 가격을 가져오기 위해 환경 참조
        self.environment = environment
        self.init_balance = initial_balance # 초기 자본금

        # 최소 단일 매매 금액과 최대 단일 매매 금액.
        self.min_trading_price = min_trading_price
        self.max_trading_price = max_trading_price

        #agent class의 속성
        self.balance = initial_balance # 현재 현금 잔고
        self.num_stocks = 0 # 보유 주식 수
        # 포트폴리오 가치: balance + num_stocks * 현재 주식 가격
        self.portfolio_value = 00


