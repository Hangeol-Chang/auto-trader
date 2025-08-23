"""
KIS API를 사용한 국내 주식 거래 모듈

한국투자증권 API를 사용하여 국내 주식 거래를 수행합니다.
"""

import logging
from typing import Optional, Dict, Any
from . import kis_fetcher
from .. import token_manager  # 올바른 경로로 수정

log = logging.getLogger(__name__)


class KISStockAPI:
    """한국투자증권 주식 거래 API 클래스"""
    
    def __init__(self, invest_type: str = "VPS", index: int = 0):
        """
        Args:
            invest_type: 투자 타입 ("VPS": 모의투자, "REAL": 실전투자)
            index: API 키 인덱스
        """
        self.invest_type = invest_type
        self.index = index
        
    def place_stock_order(self, stock_code: str, order_type: str, price: Optional[int] = None, 
                         quantity: int = 1, order_div: str = "01") -> Optional[Dict[str, Any]]:
        """
        국내 주식 주문 실행
        
        Args:
            stock_code: 종목코드 (6자리, 예: "005930")
            order_type: 주문구분 ("01": 지정가, "03": 시장가)
            price: 주문가격 (지정가 주문시 필요)
            quantity: 주문수량
            order_div: 주문구분 ("01": 매수, "02": 매도)
            
        Returns:
            주문 결과 딕셔너리 또는 None
        """
        try:
            # KIS API 매수 주문 TR ID
            if order_div == "01":  # 매수
                tr_id = "TTTC0802U"  # 실전투자 매수
            else:  # 매도
                tr_id = "TTTC0801U"  # 실전투자 매도
                
            url = '/uapi/domestic-stock/v1/trading/order-cash'
            
            # 주문 파라미터 구성
            params = {
                "CANO": self._get_account_no(),  # 계좌번호 앞 8자리
                "ACNT_PRDT_CD": self._get_account_product_cd(),  # 계좌번호 뒤 2자리
                "PDNO": stock_code,  # 종목코드
                "ORD_DVSN": order_type,  # 주문구분 (01: 지정가, 03: 시장가)
                "ORD_QTY": str(quantity),  # 주문수량
                "ORD_UNPR": str(price) if price else "0",  # 주문단가 (시장가는 0)
            }
            
            log.info("KIS 주식 주문 요청 - 종목: %s, 구분: %s, 수량: %s, 가격: %s", 
                    stock_code, "매수" if order_div == "01" else "매도", quantity, price)
            
            # API 호출
            response = kis_fetcher.url_fetch(
                api_url=url,
                ptr_id=tr_id,
                tr_cont="",
                params=params,
                postFlag=True,
                invest_type=self.invest_type,
                index=self.index
            )
            
            if response and response.isOK():
                result = response.getBody()
                log.info("KIS 주식 주문 성공 - 주문번호: %s", getattr(result, 'odno', 'N/A'))
                return {
                    "success": True,
                    "order_no": getattr(result, 'odno', ''),
                    "message": getattr(result, 'msg1', ''),
                    "rt_cd": getattr(result, 'rt_cd', ''),
                }
            else:
                error_msg = response.getErrorMessage() if response else "API 호출 실패"
                log.error("KIS 주식 주문 실패: %s", error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "rt_cd": response.getErrorCode() if response else "UNKNOWN"
                }
                
        except Exception as e:
            log.error("KIS 주식 주문 중 오류: %s", e)
            return {
                "success": False,
                "error": str(e)
            }
    
    def buy_stock(self, stock_code: str, price: Optional[int] = None, quantity: int = 1) -> Optional[Dict[str, Any]]:
        """
        주식 매수 주문
        
        Args:
            stock_code: 종목코드
            price: 주문가격 (None이면 시장가)
            quantity: 주문수량
        """
        order_type = "01" if price else "03"  # 지정가 or 시장가
        return self.place_stock_order(stock_code, order_type, price, quantity, "01")
    
    def sell_stock(self, stock_code: str, price: Optional[int] = None, quantity: int = 1) -> Optional[Dict[str, Any]]:
        """
        주식 매도 주문
        
        Args:
            stock_code: 종목코드
            price: 주문가격 (None이면 시장가)
            quantity: 주문수량
        """
        order_type = "01" if price else "03"  # 지정가 or 시장가
        return self.place_stock_order(stock_code, order_type, price, quantity, "02")
    
    def get_stock_balance(self) -> Optional[Dict[str, Any]]:
        """
        주식 잔고 조회
        
        Returns:
            잔고 정보 딕셔너리 또는 None
        """
        try:
            tr_id = "TTTC8434R"  # 주식잔고조회
            url = '/uapi/domestic-stock/v1/trading/inquire-balance'
            
            params = {
                "CANO": self._get_account_no(),
                "ACNT_PRDT_CD": self._get_account_product_cd(),
                "AFHR_FLPR_YN": "N",  # 시간외단일가여부
                "OFL_YN": "",  # 오프라인여부
                "INQR_DVSN": "02",  # 조회구분 (01: 대출일별, 02: 종목별)
                "UNPR_DVSN": "01",  # 단가구분 (01: 기본값)
                "FUND_STTL_ICLD_YN": "N",  # 펀드결제분포함여부
                "FNCG_AMT_AUTO_RDPT_YN": "N",  # 융자금액자동상환여부
                "PRCS_DVSN": "00",  # 처리구분 (00: 전일매매포함)
                "CTX_AREA_FK100": "",  # 연속조회검색조건100
                "CTX_AREA_NK100": ""   # 연속조회키100
            }
            
            response = kis_fetcher.url_fetch(
                api_url=url,
                ptr_id=tr_id,
                tr_cont="",
                params=params,
                invest_type=self.invest_type,
                index=self.index
            )
            
            if response and response.isOK():
                result = response.getBody()
                return {
                    "success": True,
                    "balances": getattr(result, 'output1', []),
                    "summary": getattr(result, 'output2', [])
                }
            else:
                error_msg = response.getErrorMessage() if response else "API 호출 실패"
                log.error("주식 잔고 조회 실패: %s", error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except Exception as e:
            log.error("주식 잔고 조회 중 오류: %s", e)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_stock_price(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        주식 현재가 조회
        
        Args:
            stock_code: 종목코드
            
        Returns:
            주가 정보 딕셔너리 또는 None
        """
        try:
            tr_id = "FHKST01010100"  # 주식현재가 시세
            url = '/uapi/domestic-stock/v1/quotations/inquire-price'
            
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",  # 시장분류코드
                "FID_INPUT_ISCD": stock_code,   # 종목코드
            }
            
            response = kis_fetcher.url_fetch(
                api_url=url,
                ptr_id=tr_id,
                tr_cont="",
                params=params,
                invest_type=self.invest_type,
                index=self.index
            )
            
            if response and response.isOK():
                result = response.getBody()
                output = getattr(result, 'output', {})
                return {
                    "success": True,
                    "stock_code": stock_code,
                    "current_price": getattr(output, 'stck_prpr', '0'),
                    "change": getattr(output, 'prdy_vrss', '0'),
                    "change_rate": getattr(output, 'prdy_ctrt', '0'),
                    "volume": getattr(output, 'acml_vol', '0'),
                }
            else:
                error_msg = response.getErrorMessage() if response else "API 호출 실패"
                log.error("주식 현재가 조회 실패: %s", error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except Exception as e:
            log.error("주식 현재가 조회 중 오류: %s", e)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_account_no(self) -> str:
        """계좌번호 앞 8자리 반환"""
        try:
            keys = token_manager.get_keys(self.invest_type, self.index)
            account_no = str(keys.get('CANO', ''))  # CANO를 문자열로 변환
            return account_no[:8] if account_no else ''
        except Exception:
            return ''
    
    def _get_account_product_cd(self) -> str:
        """계좌번호 뒤 2자리 반환"""
        try:
            keys = token_manager.get_keys(self.invest_type, self.index)
            account_no = str(keys.get('CANO', ''))  # CANO를 문자열로 변환
            return account_no[8:10] if len(account_no) >= 10 else '01'  # 기본값 '01'
        except Exception:
            return '01'  # 기본값 '01'
