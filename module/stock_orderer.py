
class Orderer:
    """
        주문 실행 모듈 인터페이스
    """


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
BACKTEST_FILEPATH = "data/backtest/state.json"
class BackTest_Orderer(Orderer):
    """
        백테스트용 주문 실행 모듈

        - order_type : "limit" (지정가) 또는 "market" (시장가)
        - ticker : 종목 코드
        - quantity : 주문 수량
        - price : 주문 가격
    """

    def __init__(self, trader):
        self.trader = trader

    def buy(self, ticker, quantity, price, order_type="market"):
        pass

    def sell(self, ticker, quantity, price, order_type="market"):
        pass