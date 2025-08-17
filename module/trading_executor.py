"""매매 실행 로직을 처리하는 모듈.

업비트 매수/매도 신호를 받아 실제 주문을 실행하는 기능을 제공합니다.
"""

import logging
from typing import Optional
from .upbit_api import UpbitAPI

log = logging.getLogger(__name__)

class TradingExecutor:
    """매매 실행기"""
    
    def __init__(self, upbit_api: UpbitAPI):
        self.api = upbit_api
        # 매매 전략 설정
        self.max_position_ratio = 0.2  # 각 종목 최대 비중 (20%)
        self.min_order_amount = 5000   # 최소 주문 금액 (원)
        self.min_sell_value = 1000     # 최소 매도 가치 (원)
    
    def execute_buy_signal(self, ticker: str) -> bool:
        """매수 신호 실행 - 해당 종목이 전체 자산의 설정된 비중을 넘지 않도록 매수"""
        try:
            # 티커로 정확한 마켓 코드 찾기
            market = self.api.find_market_by_ticker(ticker)
            if not market:
                log.error("매수 실패: 티커 '%s'에 해당하는 마켓을 찾을 수 없습니다.", ticker)
                return False
            
            # 코인 심볼 추출
            coin_symbol = market.replace('KRW-', '')
            
            # 전체 자산 계산
            total_balance = self.api.calculate_total_balance()
            target_percentage = self.max_position_ratio  # 설정된 최대 비중 사용
            target_amount = total_balance * target_percentage
            
            log.info("전체 자산: %s원, 목표 비중: %s%% (%s원)", total_balance, target_percentage*100, target_amount)
            
            # 현재 해당 코인 보유량 확인
            current_coin_balance = self.api.get_coin_balance(coin_symbol)
            current_coin_value = 0
            
            # 현재 코인 가치 계산
            if current_coin_balance > 0:
                current_price = self.api.get_current_price(market)
                if current_price:
                    current_coin_value = current_coin_balance * current_price
                    log.info("현재 %s 보유량: %s개, 가치: %s원", coin_symbol, current_coin_balance, current_coin_value)
                else:
                    log.error("현재가 조회 실패")
                    return False
            else:
                log.info("현재 %s 보유량: 0개", coin_symbol)
            
            # 추가로 매수할 수 있는 금액 계산
            available_buy_amount = target_amount - current_coin_value
            
            if available_buy_amount <= 0:
                log.warning("이미 %s가 목표 비중(%s%%)을 달성했습니다. 현재 가치: %s원, 목표: %s원", 
                           coin_symbol, target_percentage*100, current_coin_value, target_amount)
                return False
            
            # 업비트 최소 주문 금액 확인
            if available_buy_amount < self.min_order_amount:
                log.warning("매수 가능 금액이 최소 주문 금액보다 작습니다: %s원 (최소: %s원)", 
                           available_buy_amount, self.min_order_amount)
                return False
            
            # 주문 금액을 원 단위로 반올림
            buy_amount = round(available_buy_amount)
            
            log.info("매수 신호 처리 - 티커: %s, 마켓: %s", ticker, market)
            log.info("현재 보유 가치: %s원, 목표 가치: %s원, 매수 금액: %s원", 
                    current_coin_value, target_amount, buy_amount)
            
            # 시장가 매수 주문 (업비트에서는 ord_type='price' 사용)
            result = self.api.place_order(market, 'bid', price=buy_amount)
            
            if result:
                log.info("매수 주문 성공 - 마켓: %s, 금액: %s원", market, buy_amount)
                log.info("매수 후 예상 %s 가치: %s원 (전체 자산 대비 %s%%)", 
                        coin_symbol, current_coin_value + buy_amount, 
                        ((current_coin_value + buy_amount) / total_balance) * 100)
                return True
            else:
                log.error("매수 주문 실패 - 마켓: %s", market)
                return False
        except Exception as e:
            log.error("매수 신호 실행 중 오류: %s", e)
            return False
    
    def execute_sell_signal(self, ticker: str, sell_price: Optional[float] = None) -> bool:
        """매도 신호 실행 - 해당 코인 전량 매도
        
        Args:
            ticker: 매도할 코인 티커
            sell_price: 지정가 매도 가격 (None이면 시장가 매도)
        """
        try:
            # 티커로 정확한 마켓 코드 찾기
            market = self.api.find_market_by_ticker(ticker)
            if not market:
                log.error("매도 실패: 티커 '%s'에 해당하는 마켓을 찾을 수 없습니다.", ticker)
                return False
            
            # 코인 심볼 추출 (KRW- 제거)
            coin_symbol = market.replace('KRW-', '')
            
            # 해당 코인 수량 확인
            coin_balance = self.api.get_coin_balance(coin_symbol)
            
            if not coin_balance or coin_balance <= 0:
                log.warning("매도할 %s 코인이 없습니다. (잔고: %s)", coin_symbol, coin_balance)
                return False
            
            # 최소 매도 수량 확인 (매우 작은 수량은 매도 불가)
            current_price = self.api.get_current_price(market)
            if current_price:
                estimated_value = coin_balance * current_price
                if estimated_value < self.min_sell_value:  # 설정된 최소 매도 가치 사용
                    log.warning("매도 예상 금액이 너무 작습니다: %s원 (수량: %s %s, 최소: %s원)", 
                               estimated_value, coin_balance, coin_symbol, self.min_sell_value)
                    return False
            
            # 지정가 vs 시장가 결정
            if sell_price:
                # 지정가 매도
                log.info("지정가 매도 신호 처리 - 티커: %s, 마켓: %s, 수량: %s, 가격: %s원", 
                        ticker, market, coin_balance, sell_price)
                
                # 지정가 매도 주문 (업비트에서는 ord_type='limit' 사용)
                result = self.api.place_order(market, 'ask', volume=coin_balance, price=sell_price, ord_type='limit')
                
                if result:
                    log.info("지정가 매도 주문 성공 - 마켓: %s, 수량: %s, 가격: %s원", market, coin_balance, sell_price)
                    return True
                else:
                    log.error("지정가 매도 주문 실패 - 마켓: %s", market)
                    return False
            else:
                # 시장가 매도 (기존 로직)
                log.info("시장가 매도 신호 처리 - 티커: %s, 마켓: %s, 수량: %s", ticker, market, coin_balance)
                
                # 시장가 매도 주문 (업비트에서는 ord_type='market' 사용)
                result = self.api.place_order(market, 'ask', volume=coin_balance)
                
                if result:
                    log.info("시장가 매도 주문 성공 - 마켓: %s, 수량: %s", market, coin_balance)
                    return True
                else:
                    log.error("시장가 매도 주문 실패 - 마켓: %s", market)
                    return False
                    
        except Exception as e:
            log.error("매도 신호 실행 중 오류: %s", e)
            return False
    
    def get_trading_config(self) -> dict:
        """현재 매매 전략 설정값 반환"""
        return {
            "max_position_ratio": self.max_position_ratio,
            "max_position_percentage": f"{self.max_position_ratio * 100}%",
            "min_order_amount": self.min_order_amount,
            "min_sell_value": self.min_sell_value
        }
