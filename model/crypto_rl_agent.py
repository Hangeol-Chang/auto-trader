"""
Crypto Reinforcement Learning Agent

crypto 데이터를 이용한 강화학습 에이전트
quantylab의 Agent 클래스를 기반으로 crypto 거래에 특화된 에이전트
"""

import numpy as np
from quantylab import utils

class CryptoAgent:
    # 에이전트의 상태 수
    STATE_DIM = 3
    """
    암호화폐 보유 비율, 현재 손익, 평균 매수 대비 등락률 -> 3개의 상태를 가짐.
    """

    # 매매 수수료 (Upbit 기준)
    TRADING_CHARGE = 0.0005  # 거래 수수료 0.05%

    # 행동
    ACTION_BUY = 0   # 매수
    ACTION_SELL = 1  # 매도
    ACTION_HOLD = 2  # 관망 (보유)
    # 인공 신경망에서 확률을 구할 행동들
    ACTIONS = [ACTION_BUY, ACTION_SELL, ACTION_HOLD]
    NUM_ACTIONS = len(ACTIONS)

    def __init__(self, environment, initial_balance, min_trading_price, max_trading_price):
        # 현재 암호화폐 가격을 가져오기 위해 환경 참조
        self.environment = environment
        self.init_balance = initial_balance  # 초기 자본금

        # 최소 단일 매매 금액과 최대 단일 매매 금액
        self.min_trading_price = min_trading_price
        self.max_trading_price = max_trading_price

        # agent class의 속성
        self.balance = initial_balance  # 현재 현금 잔고
        self.num_coins = 0  # 보유 암호화폐 수량
        # 포트폴리오 가치: balance + num_coins * 현재 암호화폐 가격
        self.portfolio_value = 0
        self.num_buy = 0     # 매수 횟수
        self.num_sell = 0    # 매도 횟수
        self.num_hold = 0    # 관망 횟수

        self.ratio_hold = 0  # 암호화폐 보유 비율
        self.profitloss = 0  # 손익률
        self.avg_buy_price = 0  # 평균 매수 단가

    def reset(self):
        """에이전트의 상태를 초기화"""
        self.balance = self.init_balance
        self.num_coins = 0
        self.portfolio_value = self.init_balance
        self.num_buy = 0
        self.num_sell = 0
        self.num_hold = 0
        self.ratio_hold = 0
        self.profitloss = 0
        self.avg_buy_price = 0

    def set_balance(self, balance):
        self.init_balance = balance

    def get_status(self):
        """현재 에이전트의 상태를 반환"""
        current_price = self.environment.get_price()
        self.portfolio_value = self.balance + self.num_coins * current_price
        self.ratio_hold = (self.num_coins * current_price) / self.portfolio_value if self.portfolio_value > 0 else 0
        self.profitloss = (self.portfolio_value / self.init_balance) - 1
        
        return (
            self.ratio_hold,
            self.profitloss,
            (current_price / self.avg_buy_price) - 1 if self.avg_buy_price > 0 else 0
        )

    def decide_action(self, pred_value, pred_policy, epsilon):
        """에이전트 행동 결정 함수"""
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

    def validate_action(self, action):
        """유효성 검사"""
        if action == CryptoAgent.ACTION_BUY:
            # 적어도 최소 거래 금액 이상 살 수 있는지 확인
            min_required = self.min_trading_price * (1 + self.TRADING_CHARGE)
            if self.balance < min_required:
                return False
        elif action == CryptoAgent.ACTION_SELL:
            # 적어도 최소 거래 금액 이상 팔 수 있는지 확인
            current_price = self.environment.get_price()
            if self.num_coins * current_price < self.min_trading_price:
                return False
        return True

    def decide_trading_unit(self, confidence):
        """행동의 신뢰도에 따른 매수/매도 단위 조정"""
        if np.isnan(confidence):
            return self.min_trading_price
        
        current_price = self.environment.get_price()
        
        # 신뢰도에 따른 거래 금액 계산
        added_trading_price = max(min(
            int(confidence * (self.max_trading_price - self.min_trading_price)),
            self.max_trading_price - self.min_trading_price), 0)
        trading_price = self.min_trading_price + added_trading_price
        
        # 암호화폐 수량으로 변환
        trading_unit = trading_price / current_price
        return trading_unit

    def act(self, action, confidence):
        """에이전트 행동 수행 함수"""
        if not self.validate_action(action):
            action = CryptoAgent.ACTION_HOLD

        curr_price = self.environment.get_price()

        # 매수
        if action == CryptoAgent.ACTION_BUY:
            trading_unit = self.decide_trading_unit(confidence)
            # 수수료를 적용한 총 매수 금액 계산
            invest_amount = trading_unit * curr_price * (1 + self.TRADING_CHARGE)
            
            # 보유 현금이 모자랄 경우 보유 현금으로 가능한 최대한 매수
            if invest_amount > self.balance:
                invest_amount = self.balance
                trading_unit = invest_amount / (curr_price * (1 + self.TRADING_CHARGE))
            
            if trading_unit > 0:
                # 평균 매수 단가 갱신
                total_coins = self.num_coins + trading_unit
                self.avg_buy_price = (
                    (self.avg_buy_price * self.num_coins + curr_price * trading_unit) / total_coins
                    if total_coins > 0 else curr_price
                )
                self.balance -= invest_amount
                self.num_coins += trading_unit
                self.num_buy += 1

        # 매도
        elif action == CryptoAgent.ACTION_SELL:
            trading_unit = self.decide_trading_unit(confidence) / curr_price
            trading_unit = min(trading_unit, self.num_coins)  # 보유 수량보다 많을 수 없음
            
            # 수수료를 적용한 매도 금액 계산
            sell_amount = trading_unit * curr_price * (1 - self.TRADING_CHARGE)
            
            if trading_unit > 0:
                self.num_coins -= trading_unit
                self.balance += sell_amount
                self.num_sell += 1
                
                # 모든 코인을 매도한 경우 평균 매수 단가 초기화
                if self.num_coins == 0:
                    self.avg_buy_price = 0

        # 관망
        elif action == CryptoAgent.ACTION_HOLD:
            self.num_hold += 1

        # 포트폴리오 가치 갱신
        self.portfolio_value = self.balance + self.num_coins * curr_price
        self.profitloss = (self.portfolio_value / self.init_balance) - 1
        return self.profitloss
