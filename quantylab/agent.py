
# Agent class
'''
- 투자 행동을 수행하고 보유 주식을 관리
'''

from email import utils
import numpy as np
from quantylab import utils

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
        self.portfolio_value = 0
        self.num_buy = 0    # 매수 횟수
        self.num_sell = 0   # 매도 횟수
        self.num_hold = 0   # 관망 횟수

        self.ratio_hold = 0 # 주식 보유 비율
        self.profitloss = 0 # 손익률
        self.avg_buy_price = 0 # 주당 매수 단가

    def reset(self):
        # 에이전트의 상태를 초기화
        self.balance = self.init_balance
        self.num_stocks = 0
        self.portfolio_value = self.init_balance
        self.num_buy = 0
        self.num_sell = 0
        self.num_hold = 0
        self.ratio_hold = 0
        self.profitloss = 0
        self.avg_buy_price = 0

    def set_balance(self, balance):
        self.initial_balance = balance

    def get_status(self):
        self.ratio_hold = self.num_stocks * self.environment.get_price() / self.portfolio_value
        return (
            self.ratio_hold, 
            self.profitloss, 
            (self.environment.get_price() / self.avg_buy_price) - 1 if self.avg_buy_price > 0 else 0
        )
    

    # 에이전트 행동 결정 함수
    def decide_action(self, pred_value, pred_policy, epsilon):
        confidence = 0.

        pred = pred_policy
        if pred is None:
            pred = pred_value
        
        if pred is None:
            # 예측 값이 없을 경우 탐험
            epsilon = 1
        else:
            # 값이 모두 같은 경우 탐험
            maxpred = np.max(pred)
            if (pred == maxpred).all():
                epsilon = 1
        
        # 탐험 결정
        if np.random.rand() < epsilon:
            # epsilon이 클수록 탐험할 확률이 높아짐
            exploration = True
            action = np.random.randint(self.NUM_ACTIONS)
        else:
            # 탐험하지 않고 예측된 행동을 따름
            exploration = False
            action = np.argmax(pred)
        
        confidence = .5
        if pred_policy is not None:
            confidence = pred[action]
        elif pred_value is not None:
            confidence = utils.sigmoid(pred[action])
        
        return action, confidence, exploration
    
    # 유효성 검사
    def validate_action(self, action):
        if action == Agent.ACTION_BUY:
            # 적어도 1주 이상 살 수 있는지 확인
            if self.balance < self.environment.get_price() * (1 + self.TRADING_CHARGE):
                return False
        elif action == Agent.ACTION_SELL:
            # 적어도 1주 이상 팔 수 있는지 확인
            if self.num_stocks < 1:
                return False
        return True

    # 행동의 신뢰도에 따른 매수/매도 단위 조정
    def decide_trading_unit(self, confidence):
        if np.isnan(confidence):
            return self.min_trading_price
        added_trading_price = max(min(
            int(confidence * (self.max_trading_price - self.min_trading_price)),
            self.max_trading_price - self.min_trading_price), 0)
        trading_price = self.min_trading_price + added_trading_price
        return max(int(trading_price / self.environment.get_price()), 1)

    # 에이전트 행동 수행 함수
    def act(self, action, confidence):
        if not self.validate_action(action):
            action = Agent.ACTION_HOLD

        curr_price = self.environment.get_price()

        # 매수
        if action == Agent.ACTION_BUY:
            trading_unit = self.decide_trading_unit(confidence)
            balance = (
                self.balance - 
                curr_price * (1 + self.TRADING_CHARGE) * trading_unit
            )
            # 보유 현금이 모자랄 경우 보유 현금으로 가능한 최대한 매수
            if balance < 0:
                trading_unit = min(
                    int(self.balance / curr_price * (1 + self.TRADING_CHARGE)),
                    int(self.max_trading_price / curr_price)
                )
            # 수수료를 적용하여 총 매수 금액 산정
            invest_amount = curr_price * (1 + self.TRADING_CHARGE) * trading_unit
            if invest_amount > 0:
                self.avg_buy_price = \
                    (self.avg_buy_price * self.num_stocks + curr_price * trading_unit) \
                    / (self.num_stocks + trading_unit) # 평균 매수 단가 갱신
                self.balance -= invest_amount
                self.num_stocks += trading_unit
                self.num_buy += 1
        
        # 매도
        elif action == Agent.ACTION_SELL:
            trading_unit = self.decide_trading_unit(confidence)
            trading_unit = min(trading_unit, self.num_stocks) # 보유 주식 수보다 많을 수 없음
            
            invest_amount = curr_price * (
                1 - (self.TRADING_TAX + self.TRADING_CHARGE)) * trading_unit
            if invest_amount > 0:
                self.avg_buy_price = \
                    (self.avg_buy_price * self.num_stocks - curr_price) \
                    / (self.num_stocks - trading_unit) \
                    if self.num_stocks > trading_unit else 0
                self.num_stocks -= trading_unit
                self.balance += invest_amount
                self.num_sell += 1
        
        # 관망
        elif action == Agent.ACTION_HOLD:
            self.num_hold += 1
        
        # 포트폴리오 가치 갱신
        self.portfolio_value = self.balance + self.num_stocks * curr_price
        self.profitloss = (self.portfolio_value / self.initial_balance) - 1
        return self.profitloss
    