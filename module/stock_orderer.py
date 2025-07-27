
import json
import os
from datetime import datetime
from strategy.strategy import SignalType, TradingSignal

BACKTEST_FILEPATH = "data/state/backtest/"
PAPER_FILEPATH = "data/state/paper/"
LIVE_FILEPATH = "data/state/"

class Orderer:
    """
        주문 실행 모듈 인터페이스
    """

    def save_state(self, state):
        """
        상태를 저장하는 메서드
        - 초기 자본금, 보유 종목, 거래 기록 등을 저장합니다.
        - state_{YYMMDD}.json 에 저장
        - backtest의 경우 state_{YYMMDD_HHMMSS}.json 형식으로 저장 -> 설마 초당 1회 이상 호출 하겠어? ㅋㅋ

        """
        raise NotImplementedError("This method should be overridden by subclasses")
    
    def load_state(self):
        """
        상태를 로드하는 메서드
        - 초기 자본금, 보유 종목, 거래 기록 등을 로드합니다.
        """
        raise NotImplementedError("This method should be overridden by subclasses")
    
    def place_order(self, order_info):
        """
        주문을 실행하는 메서드
        - ticker: 종목 코드
        - quantity: 주문 수량
        - price: 주문 가격
        - order_type: "limit" (지정가) 또는 "market" (시장가)
        """
        raise NotImplementedError("This method should be overridden by subclasses")

"""
    state.json
    {
        "balance": 10000000,  # 초기 자본금
        "holdings": {
            "ticker": {
                "quantity": 0,  # 보유 수량
                "average_price": 0.0,  # 평균 매입가
            }
        },  # 보유 종목
        "trades": [],  # 거래 기록
    }
"""
class BackTest_Orderer(Orderer):
    """
        백테스트용 주문 실행 모듈

        - order_type : "limit" (지정가) 또는 "market" (시장가)
        - ticker : 종목 코드
        - quantity : 주문 수량
        - price : 주문 가격
    """

    def end_test(self):
        """
        백테스트 종료 메서드
        - 백테스트 결과를 저장하고 상태를 초기화합니다.
        """
        print("Ending backtest and saving state...")
        self.save_state(self.state)

    def save_state(self, state):
        """
        상태를 저장하는 메서드
        - 초기 자본금, 보유 종목, 거래 기록 등을 저장합니다.
        - state_{YYMMDD_HHMMSS}.json 형식으로 저장
        """

        # portfolio Value 계산
        portfolioValue = self.state['balance'] + sum(
            pos['quantity'] * pos['current_price'] for pos in self.state['positions'].values()
        )
        self.state['portfolioValue'] = portfolioValue  # 포트폴리오 가치 업데이트

        if not os.path.exists(self.filepath):
            os.makedirs(self.filepath)
        filename = f"state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.filepath, filename)
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=4)
        print(f"State saved to {filepath}")
        

    def load_state(self):
        # 초기 자본금, 보유 종목, 거래 기록 등을 로드합니다.
        # 예시로 빈 상태를 반환
        return {
            "balance": 10000000,        # 초기 자본금 항상 1000만원
            "portfolioValue": 10000000,        # 포트폴리오 가치
            "positions": {},         # 보유 종목
            "trade_history": [],     # 거래 기록
            "last_update": datetime.now().isoformat(),  # 마지막 업데이트 시간
            "status": "running"      # 상태 (running, stopped 등)
        }

    def __init__(self):
        self.filepath = BACKTEST_FILEPATH
        self.state = self.load_state()

    '''
        TradingSignal(
            timestamp=datetime.datetime(2025, 7, 27, 16, 52, 6, 370110), 
            signal_type=<SignalType.BUY: 'BUY'>, 
            target_time='20241216', 
            ticker='035420', 
            current_price=214000, 
            position_size=0.2, 
            quantity=None, 
            confidence=0.55
        )
    '''
    def place_order(self, order_info):
        # 주문 정보를 바탕으로 주문을 실행합니다.
        # order_info는 딕셔너리 형태로, 필요한 정보를 포함해야 합니다.

        if not isinstance(order_info, TradingSignal):
            raise ValueError("order_info must be a dictionary")

        signal_type = order_info.signal_type
        ticker = order_info.ticker

        position_size = float(order_info.position_size)

        quantity = order_info.quantity
        current_price = float(order_info.current_price)
        target_time = order_info.target_time
        confidence = order_info.confidence
        # timestamp = order_info.get('timestamp', datetime.datetime.now().isoformat())

        if signal_type not in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]:
            raise ValueError("Invalid signal_type. Must be BUY, SELL, or HOLD.")
        
        print('start place order', order_info.signal_type)
        # state에 ticker가 있으면 current_price 업데이트
        if ticker in self.state['positions']:
            self.state['positions'][ticker]['current_price'] = current_price

        if signal_type == SignalType.BUY:
            # if quantity is None:
            #     raise ValueError("Quantity must be specified for BUY orders.")
            quantity = int(self.state['balance'] * position_size / current_price) if quantity is None else quantity

            print(f"Placing BUY order for {ticker} at {current_price} with quantity {quantity} on {target_time}.")

            # 주문 실행 로직 (예: API 호출, 데이터베이스 업데이트 등)
            # 이미 보유하고 있는 종목이면
            if ticker in self.state['positions']:
                average_price = self.state['positions'][ticker]['average_price']
                # 평균 매입가 업데이트
                self.state['positions'][ticker]['average_price'] = (
                    (average_price * self.state['positions'][ticker]['quantity'] + quantity * current_price) /
                    (self.state['positions'][ticker]['quantity'] + quantity)
                )

                self.state['positions'][ticker]['quantity'] += quantity
                self.state['positions'][ticker]['average_price'] = average_price
                self.state['positions'][ticker]['last_update'] = datetime.now().isoformat()
                
            else:
                # 새 종목이면
                self.state['positions'][ticker] = {
                    'quantity': quantity,
                    'average_price': current_price,
                    'current_price': current_price,
                }

            self.state['balance'] -= quantity * current_price  # 잔액 업데이트

        elif signal_type == SignalType.SELL:
            # if quantity is None:
            #     raise ValueError("Quantity must be specified for SELL orders.")
            # print(type(self.state['positions'][ticker]['quantity']))
            if ticker not in self.state['positions']:
                # 팔 게 없을 떄 패스
                pass
            else:
                print("asd")
                print(self.state['positions'][ticker]['quantity'], position_size)
                quantity = int(self.state['positions'][ticker]['quantity'] * position_size) if quantity is None else quantity
                print(f"Placing SELL order for {ticker} at {current_price} with quantity {quantity} on {target_time}.")

                # 주문 실행 로직 (예: API 호출, 데이터베이스 업데이트 등)
                self.state['positions'][ticker]['quantity'] -= quantity
                self.state['balance'] += quantity * current_price
                
                if self.state['positions'][ticker]['quantity'] <= 0:
                    del self.state['positions'][ticker]
        else:
            pass
            # raise ValueError(f"Unknown signal type: {signal_type}")
        

        # 거래 기록에 추가
        self.state['trade_history'].append({
            'target_time': target_time,
            'signal_type': signal_type.value,
            'ticker': ticker,
            'position_size': position_size,
            'current_price': current_price,
            'quantity': quantity,
            'confidence': confidence
        })

class Paper_Orderer(Orderer):
    """
        모의 거래용 주문 실행 모듈
    """

    def __init__(self):
        self.filepath = PAPER_FILEPATH
        self.state = self.load_state()

class Live_Orderer(Orderer):
    """
        실시간 거래용 주문 실행 모듈
    """

    def save_state(self, state):
        pass

    def load_state(self):
        # KIS에 검색해서 일치하는지도 확인해야함.
        pass

    def __init__(self):
        self.filepath = LIVE_FILEPATH
        self.state = self.load_state()