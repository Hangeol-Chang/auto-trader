
"""
    자동 트레이딩 모듈

    부착될 모듈들
    - strategy : 매수, 매매 타이밍을 잡아오는 모듈
    - orderer : 실제 주문을 실행하는 모듈.
"""

import logging
import time
import pandas as pd
from module import stock_data_manager, stock_data_manager_ws
from module import stock_orderer, token_manager
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

class I_Trader:
    """
        자동 트레이딩 인터페이스
        
    """
    def __init__(self, type="VPS", **kwargs):
        self.type = type
        self.orderer = None
        self.strategy = self.set_strategy(kwargs.get('strategy', None)) 
    
    def set_strategy(self, strategy_name):
        strategy = STRATEGIES.get(strategy_name, None)
        if strategy is None:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        return strategy

    def run(self):
        """트레이딩 실행"""
        raise NotImplementedError("트레이딩 실행 메서드는 구현되지 않았습니다.")
    pass

#####################################################################################
##################### 주식 백테스트 트레이더 ###########################################
#####################################################################################
class Backtest_Trader(I_Trader):
    '''
    동작 구조
        1. 백테스트 실행 후 결과를 db에 저장
        2. 백테스트 result를 받음 <- 날짜 토큰
        3. ticker, date 이용해서 그릴 그래프 데이터를 가져옴. <- 일봉 데이터
        4. 날짜 토큰을 이용해서 db에서 거래내역을 검색.
        5. 3을 바탕으로 일봉 그래프, strategy를 보고 필요한 subplot을 그림.
        6. db에서 꺼내온 매수, 매도 신호 시각화.

    '''

    def __init__(self, **kwargs):
        super().__init__(type="backtest", **kwargs)
        """
            백테스트 트레이더 초기화
            - type : "backtest"로 고정
        """
        self.orderer = stock_orderer.BackTest_Orderer()
        self.strategy = STRATEGIES.get(kwargs.get('strategy', None), None)

        self.start_date = kwargs.get('start_date', None)
        self.end_date = kwargs.get('end_date', None)
        
        self.ticker = kwargs.get('ticker', None)

    def run(self):
        pass


#####################################################################################
##################### 주식 라이브 트레이더 #############################################
#####################################################################################
# KIS - VPS 트레이더
# KIS - PROD 트레이더
class Live_Trader(I_Trader):
    '''
    동작 구조
        1. stock finding -> 직접 입력해줄수도 있고, 추후에는 재밌는 종목을 알아서 찾도록 할 예정.
        2. web_socket을 통해 찾은 stock들의 분봉 정보를 구독.
        3. stock 데이터들의 previeous 데이터를 검색하고, 이를 dict 하나 만들어서 저장해둠. -> 검색할 때 데이터는 알아서 db에 저장
        while True:
            4. 웹소켓 신호를 기다림
            5. 웹소켓 신호가 오면, 해당 종목의 매수 매도를 알잘딱하게 결정
            6. 매수 매도 신호가 오면, orderer에 주문을 요청.

            +. 일정 주기로 관심있는 stock을 갱신.
    '''


    def __init__(self, **kwargs):
        super().__init__(type="live", **kwargs)

        self.kws = token_manager.KISWebSocket(api_url="/tryitout")

        """
            -> 현재 계좌 정보 업데이트.
            REST API - get_inquire_balance_obj - 주식잔고조회(현재잔고)
            REST API - get_inquire_balance_lst - 주식잔고조회(현재종목별 잔고)
        """

        """
            사용할 티커 정보 저장.
        """

        """ 
            ticker에 맞춰서 데이터 불러와서 저장해두기.
            REST API
        """

        pass

    def run(self):
        self.kws.start(on_result=self.on_result)
        pass

    def on_result(self, ws, tr_id, result, data_info):
        """
            웹소켓에서 받은 결과를 처리하는 메서드
        """
        print(f"WebSocket Result - TR ID: {tr_id}, Result: {result}, Data Info: {data_info}")
        # 여기에 결과 처리 로직을 추가할 수 있습니다.
        # 실제 처리 진행할 곳.


######################################################################################
##################### 코인 백테스트 트레이더  ###########################################
######################################################################################

######################################################################################
##################### 코인 라이브 트레이더 ##############################################
######################################################################################

from strategy_crypto import test_strategy
from module import crypto_orderer

import json
class Live_Crypto_Trader(I_Trader):

    def __init__(self, **kwargs):
        self.type = "live"
        self.orderer = crypto_orderer.Live_Orderer()
        self.strategy = test_strategy.Test_Strategy_Crypto()

        key_index = kwargs.get('index', 0)

        with open('private/keys.json', 'r') as f:
            keys = json.load(f)
            self.APP_KEY = keys['COIN'][key_index]['APP_KEY']
            self.APP_SECRET = keys['COIN'][key_index]['APP_SECRET']

        # 데이터 가져오기.
        self.set_data()

    def set_data(self):
        pass

    def run(self):
        """
            종목들에 대한 데이터 가져오기.
        """
        while True:
            # print("Running Live Crypto Trader...")

            time.sleep(1)  # 잠시 대기
    pass

## Legacy
#######################################################################################
##################### 트레이더 클래스 ###################################################
#######################################################################################
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
        # print("Running trader...")
        pass