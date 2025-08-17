"""Upbit API 관련 기능을 처리하는 모듈.

업비트 REST API를 사용한 주문, 잔고 조회, 시세 조회 등의 기능을 제공합니다.
"""

import json
import logging
import uuid
import requests
import hashlib
from urllib.parse import urlencode, unquote
import jwt
from typing import Optional, Dict, Any, List

log = logging.getLogger(__name__)

class UpbitAPI:
    """업비트 API 클라이언트"""
    
    def __init__(self):
        self.access_key = ''
        self.secret_key = ''
        self.market_info_cache = {}
        self.load_api_keys()
        self.load_market_info()
    
    def load_api_keys(self) -> bool:
        """업비트 API 키를 파일에서 읽어옴"""
        try:
            with open('./private/keys.json', 'r') as f:
                keys = json.load(f)
                self.access_key = keys['COIN'][0]['APP_KEY']
                self.secret_key = keys['COIN'][0]['APP_SECRET']
                log.info("업비트 API 키를 성공적으로 로드했습니다.")
                return True
        except Exception as e:
            log.error("업비트 API 키 로드 실패: %s", e)
            return False
    
    def load_market_info(self) -> bool:
        """업비트 마켓 정보를 로드하고 캐시에 저장"""
        try:
            url = "https://api.upbit.com/v1/market/all?is_details=true"
            headers = {"accept": "application/json"}
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                markets = response.json()
                
                # 심볼별로 마켓 정보를 매핑
                for market in markets:
                    market_code = market['market']  # 예: KRW-BTC
                    if market_code.startswith('KRW-'):
                        symbol = market_code.replace('KRW-', '')  # BTC
                        self.market_info_cache[symbol.upper()] = {
                            'market': market_code,
                            'korean_name': market.get('korean_name', ''),
                            'english_name': market.get('english_name', '')
                        }
                
                log.info("업비트 마켓 정보 로드 완료: %d개 마켓", len(self.market_info_cache))
                return True
            else:
                log.error("마켓 정보 로드 실패: %s", response.text)
                return False
        except Exception as e:
            log.error("마켓 정보 로드 중 오류: %s", e)
            return False
    
    def find_market_by_ticker(self, ticker: str) -> Optional[str]:
        """티커 심볼로 업비트 마켓 코드 찾기"""
        ticker_upper = ticker.upper()
        
        # 이미 KRW- 형태인 경우
        if ticker_upper.startswith('KRW-'):
            return ticker_upper
        
        # BTCKRW, ETHKRW 형태를 KRW-BTC, KRW-ETH로 변환
        if ticker_upper.endswith('KRW'):
            base_symbol = ticker_upper.replace('KRW', '')
            converted_market = f'KRW-{base_symbol}'
            log.info("티커 %s -> %s 형태로 변환", ticker, converted_market)
            
            # 변환된 마켓이 실제로 존재하는지 확인
            if base_symbol in self.market_info_cache:
                market_info = self.market_info_cache[base_symbol]
                log.info("티커 %s -> 마켓 %s (%s)", ticker, market_info['market'], market_info['korean_name'])
                return market_info['market']
            else:
                log.warning("변환된 티커 '%s'에 해당하는 업비트 마켓을 찾을 수 없습니다.", base_symbol)
                return None
        
        # 기본 티커 형태 (BTC, ETH 등)
        if ticker_upper in self.market_info_cache:
            market_info = self.market_info_cache[ticker_upper]
            log.info("티커 %s -> 마켓 %s (%s)", ticker, market_info['market'], market_info['korean_name'])
            return market_info['market']
        
        # 찾지 못한 경우
        log.warning("티커 '%s'에 해당하는 업비트 마켓을 찾을 수 없습니다.", ticker)
        log.info("지원 가능한 티커: %s", list(self.market_info_cache.keys())[:10])  # 처음 10개만 표시
        return None
    
    def get_available_tickers(self) -> List[str]:
        """사용 가능한 티커 목록 반환"""
        return list(self.market_info_cache.keys())
    
    def make_jwt_token(self, query_params: Optional[Dict] = None) -> Optional[str]:
        """업비트 JWT 토큰 생성"""
        try:
            payload = {
                'access_key': self.access_key,
                'nonce': str(uuid.uuid4()),
            }
            
            if query_params:
                query_string = unquote(urlencode(query_params, doseq=True)).encode("utf-8")
                m = hashlib.sha512()
                m.update(query_string)
                query_hash = m.hexdigest()
                payload['query_hash'] = query_hash
                payload['query_hash_alg'] = 'SHA512'
            
            # PyJWT 2.0+ 호환성을 위한 수정
            jwt_token = jwt.encode(payload, self.secret_key, algorithm='HS256')
            
            # PyJWT 2.0+에서는 문자열을 반환하므로 추가 처리 불필요
            if isinstance(jwt_token, bytes):
                jwt_token = jwt_token.decode('utf-8')
                
            return f'Bearer {jwt_token}'
        except Exception as e:
            log.error("JWT 토큰 생성 중 오류: %s", e)
            return None
    
    def get_balances(self) -> Optional[List[Dict[str, Any]]]:
        """업비트 잔고 조회"""
        try:
            url = 'https://api.upbit.com/v1/accounts'
            token = self.make_jwt_token()
            if not token:
                log.error("JWT 토큰 생성 실패")
                return None
                
            headers = {'Authorization': token}
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                log.error("잔고 조회 실패: %s", response.text)
                return None
        except Exception as e:
            log.error("잔고 조회 중 오류: %s", e)
            return None
    
    def get_current_price(self, market: str) -> Optional[float]:
        """특정 마켓의 현재가 조회"""
        try:
            url = "https://api.upbit.com/v1/ticker"
            params = {"markets": market}
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data[0]['trade_price'] if data else None
            else:
                log.error("현재가 조회 실패: %s", response.text)
                return None
        except Exception as e:
            log.error("현재가 조회 중 오류: %s", e)
            return None
    
    def calculate_total_balance(self) -> float:
        """전체 보유 자산 계산 (KRW 기준)"""
        try:
            balances = self.get_balances()
            if not balances:
                return 0
            
            total_krw = 0
            
            for balance in balances:
                currency = balance['currency']
                balance_amount = float(balance['balance'])
                
                if currency == 'KRW':
                    total_krw += balance_amount
                else:
                    # 다른 코인의 경우 KRW 가격으로 환산
                    market = f'KRW-{currency}'
                    current_price = self.get_current_price(market)
                    if current_price:
                        total_krw += balance_amount * current_price
            
            return total_krw
        except Exception as e:
            log.error("전체 잔고 계산 중 오류: %s", e)
            return 0
    
    def place_order(self, market: str, side: str, volume: Optional[float] = None, 
                   price: Optional[float] = None, ord_type: str = 'market') -> Optional[Dict[str, Any]]:
        """업비트 주문 실행"""
        try:
            url = 'https://api.upbit.com/v1/orders'
            
            params = {
                'market': market,
                'side': side,  # 'bid' (매수) 또는 'ask' (매도)
            }
            
            if side == 'bid':
                # 매수: 업비트에서는 시장가 매수 시 ord_type을 'price'로 설정
                if ord_type == 'limit' and price:
                    # 지정가 매수
                    params['ord_type'] = 'limit'
                    params['price'] = str(int(price))
                    if volume:
                        params['volume'] = str(volume)
                else:
                    # 시장가 매수 (기본)
                    params['ord_type'] = 'price'
                    if price:
                        params['price'] = str(int(price))
            elif side == 'ask':
                # 매도
                if ord_type == 'limit' and price:
                    # 지정가 매도
                    params['ord_type'] = 'limit'
                    params['price'] = str(int(price))
                    if volume:
                        params['volume'] = str(volume)
                else:
                    # 시장가 매도 (기본)
                    params['ord_type'] = 'market'
                    if volume:
                        params['volume'] = str(volume)
            
            log.info("주문 파라미터: %s", params)
            
            token = self.make_jwt_token(params)
            if not token:
                log.error("JWT 토큰 생성 실패 - 주문 취소")
                return None
                
            headers = {'Authorization': token}
            
            response = requests.post(url, json=params, headers=headers)
            if response.status_code == 201:
                log.info("주문 성공: %s", response.json())
                return response.json()
            else:
                log.error("주문 실패: %s", response.text)
                return None
        except Exception as e:
            log.error("주문 실행 중 오류: %s", e)
            return None
    
    def get_coin_balance(self, coin_symbol: str) -> float:
        """특정 코인의 보유 수량 조회"""
        try:
            balances = self.get_balances()
            if not balances:
                return 0
            
            for balance in balances:
                if balance['currency'] == coin_symbol:
                    return float(balance['balance'])
            return 0
        except Exception as e:
            log.error("코인 잔고 조회 중 오류: %s", e)
            return 0
