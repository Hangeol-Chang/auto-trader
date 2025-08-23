"""
암호화폐 주문 실행 모듈

업비트 API를 활용한 실제 암호화폐 매수/매도 주문 실행
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
from module.upbit_api import UpbitAPI

log = logging.getLogger(__name__)


class Live_Orderer:
    """실시간 암호화폐 주문 실행기"""
    
    def __init__(self, min_krw_order=5000):
        """
        Args:
            min_krw_order (int): 최소 주문 금액 (KRW)
        """
        self.upbit_api = UpbitAPI()
        self.min_krw_order = min_krw_order
        self.last_order_time = {}  # 마켓별 마지막 주문 시간
        self.order_cooldown = 1.0  # 주문 간 최소 간격 (초)
        self.last_error = None  # 마지막 오류 정보 저장
        
        log.info("Live_Orderer 초기화 완료")
    
    def place_order(self, order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        주문 실행
        
        Args:
            order_data: {
                'action': 'BUY' | 'SELL' | 'HOLD',
                'market': 'KRW-BTC',
                'confidence': 0.8,
                'current_price': 45000000.0,
                'amount_krw': 50000 (매수시) | None (매도시)
            }
            
        Returns:
            주문 결과 또는 None
        """
        try:
            action = order_data.get('action')
            market = order_data.get('market')
            confidence = order_data.get('confidence', 0.0)
            current_price = order_data.get('current_price')
            
            # 오류 정보 초기화
            self.last_error = None
            
            if not market or action == 'HOLD':
                return "HOLD"
            
            # 주문 쿨다운 체크
            if self._is_in_cooldown(market):
                log.debug(f"[{market}] 주문 쿨다운 중")
                return "COOLDOWN"
            
            # 신뢰도가 낮으면 주문하지 않음
            if confidence < 0.6:
                log.debug(f"[{market}] 낮은 신뢰도로 주문 스킵: {confidence:.3f}")
                return "LOW_CONFIDENCE"

            if action == 'BUY':
                return self._place_buy_order(market, order_data)
            elif action == 'SELL':
                return self._place_sell_order(market, order_data)
            else:
                error_msg = f"알 수 없는 액션: {action}"
                log.warning(error_msg)
                self.last_error = error_msg
                return "UNKNOWN_ACTION"
                
        except Exception as e:
            error_msg = f"주문 실행 중 오류: {e}"
            log.error(error_msg)
            self.last_error = error_msg
            return "ERROR"
    
    def _place_buy_order(self, market: str, order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """매수 주문 실행"""
        try:
            amount_krw = order_data.get('amount_krw', 10000)
            
            # 최소 주문 금액 체크
            if amount_krw < self.min_krw_order:
                error_msg = f"최소 주문 금액 미달: {amount_krw:,}원 < {self.min_krw_order:,}원"
                log.warning(f"[{market}] {error_msg}")
                self.last_error = error_msg
                return None
            
            # KRW 잔고 확인
            krw_balance = self._get_krw_balance()
            if krw_balance < amount_krw:
                error_msg = f"KRW 잔고 부족: {krw_balance:,}원 < {amount_krw:,}원"
                log.warning(f"[{market}] {error_msg}")
                self.last_error = error_msg
                return None
            
            log.info(f"[{market}] 매수 주문 실행: {amount_krw:,}원")
            
            # 시장가 매수 주문
            result = self.upbit_api.place_order(
                market=market,
                side='bid',  # 매수
                price=amount_krw,  # 시장가 매수시 총 금액
                ord_type='market'  # 업비트에서는 시장가 매수시 'price' ord_type 사용
            )
            
            if result:
                self._update_last_order_time(market)
                log.info(f"[{market}] 매수 주문 성공: {result.get('uuid')}")
                return result
            else:
                error_msg = "업비트 API에서 주문 실행 실패 (결과 없음)"
                log.error(f"[{market}] {error_msg}")
                self.last_error = error_msg
                return None
            
        except Exception as e:
            error_msg = f"매수 주문 실행 중 오류: {e}"
            log.error(f"[{market}] {error_msg}")
            self.last_error = error_msg
            return None
    
    def _place_sell_order(self, market: str, order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """매도 주문 실행"""
        try:
            # 코인 잔고 확인
            coin_symbol = market.split('-')[1]  # KRW-BTC -> BTC
            coin_balance = self.upbit_api.get_coin_balance(coin_symbol)
            
            if coin_balance <= 0:
                error_msg = f"매도할 {coin_symbol} 잔고 없음"
                log.warning(f"[{market}] {error_msg}")
                self.last_error = error_msg
                return None
            
            # 최소 주문 금액 확인 (현재가 기준)
            current_price = order_data.get('current_price')
            if current_price and (coin_balance * current_price) < self.min_krw_order:
                error_msg = f"매도 금액이 최소 주문 금액 미달: {coin_balance * current_price:,.0f}원 < {self.min_krw_order:,}원"
                log.warning(f"[{market}] {error_msg}")
                self.last_error = error_msg
                return None
            
            log.info(f"[{market}] 매도 주문 실행: {coin_balance} {coin_symbol}")
            
            # 시장가 매도 주문
            result = self.upbit_api.place_order(
                market=market,
                side='ask',  # 매도
                volume=coin_balance,  # 보유 수량 전체
                ord_type='market'  # 시장가
            )
            
            if result:
                self._update_last_order_time(market)
                log.info(f"[{market}] 매도 주문 성공: {result.get('uuid')}")
                return result
            else:
                error_msg = "업비트 API에서 주문 실행 실패 (결과 없음)"
                log.error(f"[{market}] {error_msg}")
                self.last_error = error_msg
                return None
            
        except Exception as e:
            error_msg = f"매도 주문 실행 중 오류: {e}"
            log.error(f"[{market}] {error_msg}")
            self.last_error = error_msg
            return None
    
    def _get_krw_balance(self) -> float:
        """KRW 잔고 조회"""
        try:
            balances = self.upbit_api.get_balances()
            if balances:
                for balance in balances:
                    if balance['currency'] == 'KRW':
                        return float(balance['balance'])
            return 0.0
        except Exception as e:
            log.error(f"KRW 잔고 조회 중 오류: {e}")
            return 0.0
    
    def _is_in_cooldown(self, market: str) -> bool:
        """주문 쿨다운 체크"""
        if market not in self.last_order_time:
            return False
        
        elapsed = time.time() - self.last_order_time[market]
        return elapsed < self.order_cooldown
    
    def _update_last_order_time(self, market: str):
        """마지막 주문 시간 업데이트"""
        self.last_order_time[market] = time.time()
    
    def get_balance_info(self) -> Dict[str, Any]:
        """잔고 정보 조회"""
        try:
            balances = self.upbit_api.get_balances()
            total_krw = self.upbit_api.calculate_total_balance()
            
            return {
                'balances': balances,
                'total_krw': total_krw,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            log.error(f"잔고 정보 조회 중 오류: {e}")
            return {}
