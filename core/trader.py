
"""
    자동 트레이딩 모듈

    부착될 모듈들
    - strategy : 매수, 매매 타이밍을 잡아오는 모듈
    - orderer : 실제 주문을 실행하는 모듈.
"""

import logging
import os
import time
import traceback
import pandas as pd
from module.stock import stock_data_manager, stock_data_manager_ws
from module.stock import stock_orderer
from module import token_manager
from strategy.strategy import SignalType
from strategy import    \
    ma_strategy, \
    macd_strategy, \
    squeeze_momentum_strategy, \
    rsi_strategy

from strategy.sub import \
    stop_loss_strategy

# Discord API import 추가
from core.api.discord_api import send_to_discord_webhook

# 모듈 기본 디렉토리 기준 절대 경로 설정
MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DATA_DIR = os.path.join(MODULE_ROOT, "data", "state")

logger = logging.getLogger(__name__)
log = logging.getLogger(__name__)  # 추가


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
from module.crypto import crypto_orderer
from module.crypto.crypto_data_manager import get_candle_data

import json
import threading
import websocket
import time
import zlib
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

# 하이브리드 모델 관련 import
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from model.crypto_rl_learner import CryptoReinforcementLearner
from quantylab.networks import DNNLSTMNetwork


class Live_Crypto_Trader(I_Trader):
    """
    하이브리드 모델 기반 실시간 암호화폐 트레이더
    
    업비트 웹소켓을 통해 실시간 분봉 데이터를 수신하고
    DNN+LSTM 하이브리드 모델을 사용하여 매매 신호를 생성
    """

    def __init__(self, **kwargs):
        self.type = "live_crypto"
        self.orderer = crypto_orderer.Live_Orderer()
        
        # 거래할 코인 목록 설정
        self.markets = kwargs.get('markets', ['KRW-BTC', 'KRW-ETH', 'KRW-XRP'])
        self.interval = kwargs.get('interval', '1m')  # 1분봉
        self.num_steps = kwargs.get('num_steps', 5)  # LSTM 시계열 스텝
        self.min_confidence = kwargs.get('min_confidence', 0.7)  # 최소 신뢰도
        self.trading_amount = kwargs.get('trading_amount', 10000)  # 거래 금액 (KRW)
        
        # 웹소켓 관련
        self.ws = None
        self.is_running = False
        self.shutdown_event = threading.Event()
        
        # 데이터 저장소 (각 마켓별로 최근 데이터 저장)
        self.market_data = {}
        self.models = {}  # 각 마켓별 모델
        self._last_predictions = {}  # 마켓별 마지막 예측 결과 저장
        self._last_signal_times = {}  # 마켓별 마지막 신호 생성 시간
        self._last_actions = {}  # 마켓별 마지막 실행된 액션 (중복 신호 방지용)
        
        # 초기화
        self._initialize_models()
        self._initialize_market_data()
        self._initialize_trading_states()
        
        log.info(f"Live_Crypto_Trader 초기화 완료: {self.markets}")

    def _initialize_models(self):
        """각 마켓별 하이브리드 모델 로드 (모델이 없으면 자동 학습)"""
        for market in self.markets:
            try:
                # 모델 파일 경로 찾기
                model_dir = "model/crypto_rl_models"
                model_files = []
                
                if os.path.exists(model_dir):
                    import glob
                    pattern = f"value_network_{market.replace('-', '_')}_*.weights.h5"
                    model_files = glob.glob(os.path.join(model_dir, pattern))
                
                if model_files:
                    # 가장 최신 모델 사용
                    latest_model = max(model_files, key=os.path.getmtime)
                    
                    # 모델 로드
                    learner = CryptoReinforcementLearner(
                        market=market,
                        net='dnn_lstm',
                        num_steps=self.num_steps,
                        reuse_models=True
                    )
                    
                    # 네트워크 초기화
                    learner.init_value_network()
                    
                    # 가중치 로드
                    if learner.value_network:
                        learner.value_network.load_model(latest_model)
                        self.models[market] = learner.value_network
                        log.info(f"[{market}] 모델 로드 성공: {latest_model}")
                    else:
                        log.warning(f"[{market}] 모델 네트워크 생성 실패")
                        # 모델 네트워크 생성 실패 시 자동 학습 시도
                        self._train_model_automatically(market)
                else:
                    log.warning(f"[{market}] 모델 파일을 찾을 수 없음 - 자동 학습을 시작합니다...")
                    # 모델 파일이 없으면 자동 학습
                    success = self._train_model_automatically(market)
                    if not success:
                        # 자동 학습 실패 시 기본 네트워크라도 생성
                        try:
                            learner = CryptoReinforcementLearner(
                                market=market,
                                net='dnn_lstm',
                                num_steps=self.num_steps,
                                reuse_models=False
                            )
                            learner.init_value_network()
                            if learner.value_network:
                                self.models[market] = learner.value_network
                                log.info(f"[{market}] 기본 모델 네트워크 생성 완료 (학습되지 않음)")
                            else:
                                log.warning(f"[{market}] 기본 모델 네트워크 생성도 실패")
                        except Exception as ne:
                            log.error(f"[{market}] 기본 모델 생성 중 오류: {ne}")
                    
            except Exception as e:
                log.error(f"[{market}] 모델 초기화 실패: {e}")
                # 최후의 수단으로 자동 학습 시도
                log.info(f"[{market}] 최후의 수단으로 자동 학습을 시도합니다...")
                self._train_model_automatically(market)
    
    def _train_model_automatically(self, market: str) -> bool:
        """
        특정 마켓에 대해 자동으로 모델을 학습합니다.
        
        Args:
            market: 학습할 마켓 (예: 'KRW-BTC')
            
        Returns:
            bool: 학습 성공 여부
        """
        try:
            log.info(f"[{market}] 자동 모델 학습을 시작합니다...")
            
            # 학습 함수 직접 import 및 호출
            from model.train_crypto_rl_hybrid import train_hybrid_model
            
            log.info(f"[{market}] 학습 시작 - 에피소드: 50, 학습률: 0.001")
            
            # 직접 학습 함수 호출 (빠른 학습을 위해 파라미터 조정)
            model_path, summary_path = train_hybrid_model(
                market=market,
                epochs=50,  # 빠른 학습을 위해 에피소드 수 줄임
                balance=10000000,
                num_steps=self.num_steps,
                lr=0.001,
                output_path='model/crypto_rl_models'
            )
            
            if model_path and summary_path:
                log.info(f"[{market}] 학습 완료 - 모델 로드를 시도합니다...")
                
                # 학습된 모델 로드 시도
                learner = CryptoReinforcementLearner(
                    market=market,
                    net='dnn_lstm',
                    num_steps=self.num_steps,
                    reuse_models=True
                )
                
                learner.init_value_network()
                
                if learner.value_network and model_path:
                    learner.value_network.load_model(model_path)
                    self.models[market] = learner.value_network
                    log.info(f"[{market}] 자동 학습된 모델 로드 성공: {model_path}")
                    return True
                else:
                    log.error(f"[{market}] 학습된 모델 네트워크 생성 또는 로드 실패")
                    return False
            else:
                log.error(f"[{market}] 학습 실패 - 모델 파일이 생성되지 않음")
                return False
                
        except Exception as e:
            log.error(f"[{market}] 자동 학습 중 오류: {e}")
            import traceback
            log.error(f"[{market}] 상세 오류: {traceback.format_exc()}")
            return False
    
    def _initialize_market_data(self):
        """각 마켓별 초기 데이터 로드"""
        for market in self.markets:
            try:
                # 최근 캔들 데이터 로드 (LSTM을 위해 충분한 양)
                # 현재 시간부터 100개 분봉 전까지의 데이터
                from datetime import datetime, timedelta
                now = datetime.now()
                start_time = now - timedelta(minutes=100)
                
                start_datetime = start_time.strftime('%Y%m%d%H%M')
                end_datetime = now.strftime('%Y%m%d%H%M')
                
                df = get_candle_data(
                    market=market, 
                    interval=self.interval, 
                    start_datetime=start_datetime,
                    end_datetime=end_datetime
                )
                if df is not None and len(df) > 0:
                    # 기술적 지표 계산
                    df = self._calculate_technical_indicators(df)
                    self.market_data[market] = df
                    log.info(f"[{market}] 초기 데이터 로드: {len(df)}개 캔들")
                else:
                    log.warning(f"[{market}] 초기 데이터 로드 실패")
                    self.market_data[market] = pd.DataFrame()
                    
            except Exception as e:
                log.error(f"[{market}] 초기 데이터 로드 중 오류: {e}")
                self.market_data[market] = pd.DataFrame()

    def _initialize_trading_states(self):
        """잔고 기반 초기 매수/매도 상태 설정"""
        try:
            log.info("현재 잔고를 확인하여 초기 매매 상태를 설정합니다...")
            
            # orderer가 없으면 스킵
            if not hasattr(self, 'orderer'):
                log.warning("orderer가 초기화되지 않았습니다. 잔고 기반 상태 설정을 스킵합니다.")
                return
                
            if not hasattr(self.orderer, 'upbit_api'):
                log.warning("업비트 API가 초기화되지 않았습니다. 잔고 기반 상태 설정을 스킵합니다.")
                return
            
            # 전체 잔고 조회
            balances = self.orderer.upbit_api.get_balances()
            
            if not balances:
                log.warning("잔고 조회에 실패했습니다. 모든 마켓을 매도 상태로 초기화합니다.")
                return
            
            # 현금 잔고 (KRW) 계산
            krw_balance = 0
            for balance in balances:
                if balance['currency'] == 'KRW':
                    krw_balance = float(balance['balance'])
                    break
            
            log.info(f"현재 KRW 잔고: {krw_balance:,.0f}원")
            
            # 각 코인의 현재 시세 조회 및 총 자산 계산
            total_asset_value = krw_balance
            coin_values = {}
            
            for balance in balances:
                if balance['currency'] != 'KRW' and float(balance['balance']) > 0:
                    currency = balance['currency']
                    amount = float(balance['balance'])
                    market = f"KRW-{currency}"
                    
                    # 현재 시세 조회
                    try:
                        current_price = self.orderer.upbit_api.get_current_price(market)
                        if current_price:
                            coin_value = amount * current_price
                            coin_values[market] = coin_value
                            total_asset_value += coin_value
                            log.info(f"{market}: {amount:,.4f} ({coin_value:,.0f}원)")
                    except Exception as e:
                        log.error(f"{market} 시세 조회 실패: {e}")
            
            log.info(f"총 자산 가치: {total_asset_value:,.0f}원")
            
            # 5% 이상 보유한 코인을 매수 상태로 설정
            threshold = total_asset_value * 0.05
            log.info(f"매수 상태 임계값 (5%): {threshold:,.0f}원")
            
            for market, coin_value in coin_values.items():
                if market in self.markets:
                    if coin_value >= threshold:
                        self._last_actions[market] = 'BUY'
                        log.info(f"[{market}] 매수 상태로 초기화 (보유 가치: {coin_value:,.0f}원, {coin_value/total_asset_value*100:.1f}%)")
                    else:
                        log.info(f"[{market}] 매도 상태로 초기화 (보유 가치: {coin_value:,.0f}원, {coin_value/total_asset_value*100:.1f}%)")
            
            # 모니터링 대상이지만 보유하지 않은 코인들은 매도 상태로 초기화
            for market in self.markets:
                if market not in self._last_actions:
                    log.info(f"[{market}] 매도 상태로 초기화 (미보유)")
                    
        except Exception as e:
            log.error(f"초기 매매 상태 설정 중 오류: {e}")
            log.info("모든 마켓을 매도 상태로 초기화합니다.")
    
    def _should_skip_signal(self, market, action):
        """
        신호 중복 방지 검사
        - 마지막 액션이 BUY였다면, SELL 신호가 올 때까지 BUY 신호 무시
        - 마지막 액션이 SELL이었다면, BUY 신호가 올 때까지 SELL 신호 무시
        """
        if market not in self._last_actions:
            return False  # 첫 번째 신호는 허용
        
        last_action = self._last_actions[market]
        
        # 같은 액션이 연속으로 발생하는 경우 스킵
        if last_action == action:
            log.info(f"[{market}] 중복 신호 스킵: {action} (마지막 액션: {last_action})")
            return True
        
        return False  # 다른 액션인 경우 허용
    
    def _update_last_action(self, market, action, success=True):
        """
        마지막 액션 업데이트
        - success=True: 주문이 성공한 경우에만 업데이트
        - success=False: 주문이 실패한 경우 업데이트하지 않음 (재시도 가능하도록)
        """
        if success:
            self._last_actions[market] = action
            log.info(f"[{market}] 마지막 액션 업데이트: {action}")
        else:
            log.info(f"[{market}] 주문 실패로 인한 마지막 액션 유지: {self._last_actions.get(market, 'None')}")
    
    def _send_discord_order_notification(self, order_data: dict, order_type: str = "ORDER"):
        """
        Discord로 주문 알림 전송
        
        Args:
            order_data: 주문 데이터
            order_type: "ORDER" (주문 신호) 또는 "RESULT" (주문 결과)
        """
        try:
            market = order_data.get('market', 'Unknown')
            action = order_data.get('action', 'Unknown')
            confidence = order_data.get('confidence', 0)
            current_price = order_data.get('current_price', 0)
            
            if order_type == "ORDER":
                # 주문 신호 메시지
                emoji = "🔴" if action == "SELL" else "🟢"
                title = f"{emoji} **암호화폐 매매 신호 발생**"
                
                message = f"""{title}
📊 **코인**: {market}
🎯 **신호**: {action}
💯 **신뢰도**: {confidence:.2f}
💰 **현재가**: {current_price:,.0f}원
⏰ **시간**: {order_data.get('timestamp', 'Unknown')}
📝 **사유**: {order_data.get('reason', 'No reason provided')}"""

            else:  # RESULT
                # 주문 결과 메시지
                success = order_data.get('success', False)
                uuid = order_data.get('uuid', 'Unknown')
                error_msg = order_data.get('error', '')
                
                if success:
                    emoji = "✅"
                    status_text = "주문 성공"
                    color_emoji = "🟢" if action == "BUY" else "🔴"
                else:
                    emoji = "❌"
                    status_text = "주문 실패"
                    color_emoji = "⚠️"
                
                message = f"""{emoji} **{status_text}**
{color_emoji} **코인**: {market}
🎯 **액션**: {action}
💰 **현재가**: {current_price:,.0f}원
🆔 **주문ID**: {uuid}
⏰ **시간**: {order_data.get('timestamp', 'Unknown')}"""
                
                if not success and error_msg:
                    message += f"\n❗ **오류**: {error_msg}"
            
            # Discord로 메시지 전송
            success = send_to_discord_webhook(message)
            if success:
                log.info(f"[{market}] Discord 알림 전송 성공: {order_type}")
            else:
                log.warning(f"[{market}] Discord 알림 전송 실패: {order_type}")
                
        except Exception as e:
            log.error(f"Discord 알림 전송 중 오류: {e}")
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        try:
            df = df.copy()
            
            # 가격 데이터
            close = df['trade_price']
            high = df['high_price']
            low = df['low_price']
            volume = df['candle_acc_trade_volume']
            
            # 1. 이동평균선
            df['ma5'] = close.rolling(window=5).mean()
            df['ma10'] = close.rolling(window=10).mean()
            df['ma20'] = close.rolling(window=20).mean()
            
            # 2. RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # 3. MACD
            exp1 = close.ewm(span=12, adjust=False).mean()
            exp2 = close.ewm(span=26, adjust=False).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # 4. 볼린저 밴드
            bb_period = 20
            bb_std = 2
            df['bb_middle'] = close.rolling(window=bb_period).mean()
            bb_std_dev = close.rolling(window=bb_period).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std_dev * bb_std)
            df['bb_lower'] = df['bb_middle'] - (bb_std_dev * bb_std)
            
            # 5. 스토캐스틱
            low_14 = low.rolling(window=14).min()
            high_14 = high.rolling(window=14).max()
            df['stoch_k'] = 100 * ((close - low_14) / (high_14 - low_14))
            df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
            
            # 6. 변화율
            df['price_change'] = close.pct_change()
            df['volume_change'] = volume.pct_change()
            
            # NaN 값 처리
            df = df.bfill().fillna(0)
            
            return df
            
        except Exception as e:
            log.error(f"기술적 지표 계산 중 오류: {e}")
            return df
    
    def _prepare_model_input(self, market: str) -> Optional[np.ndarray]:
        """모델 입력 데이터 준비"""
        try:
            df = self.market_data.get(market)
            if df is None or len(df) < self.num_steps:
                return None
            
            # 최근 num_steps개 데이터 선택
            recent_data = df.tail(self.num_steps).copy()
            
            # 피처 선택 (15개 특성)
            features = [
                'ma5', 'ma10', 'ma20', 'rsi', 'macd', 'macd_signal', 'macd_histogram',
                'bb_upper', 'bb_middle', 'bb_lower', 'stoch_k', 'stoch_d',
                'price_change', 'volume_change', 'trade_price'
            ]
            
            # 정규화
            feature_data = recent_data[features].values
            feature_data = (feature_data - np.mean(feature_data, axis=0)) / (np.std(feature_data, axis=0) + 1e-8)
            
            # 모델 입력 형태로 변환: (1, num_steps, features)
            model_input = feature_data.reshape(1, self.num_steps, len(features))
            
            return model_input
            
        except Exception as e:
            log.error(f"[{market}] 모델 입력 데이터 준비 중 오류: {e}")
            return None
    
    def _predict_action(self, market: str) -> Dict[str, Any]:
        """모델을 사용한 행동 예측 또는 기본 기술적 분석"""
        try:
            model = self.models.get(market)
            
            # 모델이 있을 경우 모델 예측 사용
            if model is not None:
                log.debug(f"[{market}] 모델 예측 시작")
                
                model_input = self._prepare_model_input(market)
                if model_input is None:
                    log.warning(f"[{market}] 모델 입력 데이터 준비 실패 - 기술적 분석으로 대체")
                    return self._basic_technical_analysis(market)
                
                log.debug(f"[{market}] 모델 입력 크기: {model_input.shape}")
                
                # 모델 예측
                prediction = model.predict(model_input)
                log.debug(f"[{market}] 모델 예측 완료: {prediction}")
                
                # 예측 결과 해석
                if len(prediction.shape) > 1:
                    prediction = prediction[0]
                
                # 3개 액션 (HOLD, BUY, SELL)에 대한 확률
                if len(prediction) >= 3:
                    hold_prob = prediction[0]
                    buy_prob = prediction[1] 
                    sell_prob = prediction[2]
                    
                    log.info(f"[{market}] 모델 예측 확률 - HOLD: {hold_prob:.3f}, BUY: {buy_prob:.3f}, SELL: {sell_prob:.3f}")
                    
                    max_prob = max(hold_prob, buy_prob, sell_prob)
                    
                    if buy_prob == max_prob:
                        action = 'BUY'
                    elif sell_prob == max_prob:
                        action = 'SELL'
                    else:
                        action = 'HOLD'
                    
                    confidence = float(max_prob)
                    log.info(f"[{market}] 모델 예측 결과: {action} (신뢰도: {confidence:.3f})")
                else:
                    # 단일 값인 경우
                    value = float(prediction[0] if len(prediction) > 0 else prediction)
                    log.info(f"[{market}] 모델 예측 단일값: {value:.3f}")
                    
                    if value > 0.6:
                        action = 'BUY'
                        confidence = value
                    elif value < 0.4:
                        action = 'SELL'
                        confidence = 1.0 - value
                    else:
                        action = 'HOLD'
                        confidence = 0.5
                    
                    log.info(f"[{market}] 모델 예측 결과: {action} (신뢰도: {confidence:.3f})")
                
                return {
                    'action': action,
                    'confidence': confidence,
                    'reason': f'Model prediction: {confidence:.3f}'
                }
            else:
                # 모델이 없을 경우 기본 기술적 분석 사용
                log.warning(f"[{market}] 모델이 없음 - 기술적 분석으로 대체")
                return self._basic_technical_analysis(market)
                
        except Exception as e:
            log.error(f"[{market}] 모델 예측 중 오류: {e}")
            log.error(f"[{market}] 상세 오류: {traceback.format_exc()}")
            # 오류 발생시 기본 기술적 분석으로 대체
            log.warning(f"[{market}] 기술적 분석으로 대체하여 예측 계속 진행")
            return self._basic_technical_analysis(market)
    
    def _basic_technical_analysis(self, market: str) -> Dict[str, Any]:
        """기본 기술적 분석 전략"""
        try:
            log.debug(f"[{market}] 기술적 분석 시작")
            
            df = self.market_data.get(market)
            if df is None or len(df) < 20:
                log.warning(f"[{market}] 기술적 분석용 데이터 부족 (데이터 개수: {len(df) if df is not None else 0})")
                return {'action': 'HOLD', 'confidence': 0.0, 'reason': 'Insufficient data for analysis'}
            
            # 최근 데이터
            recent = df.tail(1).iloc[0]
            log.debug(f"[{market}] 현재 가격: {recent.get('trade_price', 0):,}원")
            
            # 기본 매매 신호
            signals = []
            
            # 1. RSI 신호
            rsi = recent.get('rsi', 50)
            log.debug(f"[{market}] RSI: {rsi:.2f}")
            if rsi < 30:
                signals.append(('BUY', 0.7, 'RSI oversold'))
                log.info(f"[{market}] RSI 과매도 신호 (RSI: {rsi:.2f})")
            elif rsi > 70:
                signals.append(('SELL', 0.7, 'RSI overbought'))
                log.info(f"[{market}] RSI 과매수 신호 (RSI: {rsi:.2f})")
            
            # 2. 이동평균 신호
            price = recent.get('trade_price', 0)
            ma5 = recent.get('ma5', 0)
            ma20 = recent.get('ma20', 0)
            log.debug(f"[{market}] 가격: {price:,}, MA5: {ma5:,}, MA20: {ma20:,}")
            
            if price > ma5 > ma20:
                signals.append(('BUY', 0.6, 'Price above MA'))
                log.info(f"[{market}] 이동평균 상향돌파 신호")
            elif price < ma5 < ma20:
                signals.append(('SELL', 0.6, 'Price below MA'))
                log.info(f"[{market}] 이동평균 하향돌파 신호")
            
            # 3. MACD 신호
            macd = recent.get('macd', 0)
            macd_signal = recent.get('macd_signal', 0)
            log.debug(f"[{market}] MACD: {macd:.4f}, MACD Signal: {macd_signal:.4f}")
            
            if macd > macd_signal and macd > 0:
                signals.append(('BUY', 0.5, 'MACD bullish'))
                log.info(f"[{market}] MACD 상승 신호")
            elif macd < macd_signal and macd < 0:
                signals.append(('SELL', 0.5, 'MACD bearish'))
                log.info(f"[{market}] MACD 하락 신호")
            
            # 신호 종합
            if not signals:
                log.info(f"[{market}] 기술적 분석 - 명확한 신호 없음")
                return {'action': 'HOLD', 'confidence': 0.3, 'reason': 'No clear signals'}
            
            # 가장 강한 신호 선택
            best_signal = max(signals, key=lambda x: x[1])
            action, confidence, reason = best_signal
            
            log.info(f"[{market}] 기술적 분석 결과: {action} (신뢰도: {confidence:.3f}, 이유: {reason})")
            log.info(f"[{market}] 전체 신호들: {[f'{s[0]}({s[1]:.1f})' for s in signals]}")
            
            return {
                'action': action,
                'confidence': confidence,
                'reason': f'Technical analysis: {reason}'
            }
            
        except Exception as e:
            log.error(f"[{market}] 기술적 분석 중 오류: {e}")
            log.error(f"[{market}] 상세 오류: {traceback.format_exc()}")
            return {'action': 'HOLD', 'confidence': 0.0, 'reason': f'Analysis error: {e}'}

    def run(self):
        """트레이더 실행"""
        log.info("Live_Crypto_Trader 시작")
        
        self.is_running = True
        
        # 웹소켓 연결 시작
        self._start_websocket()
        
        # 메인 루프
        try:
            while self.is_running and not self.shutdown_event.is_set():
                time.sleep(1)
                
        except KeyboardInterrupt:
            log.info("사용자에 의한 종료 요청")
        except Exception as e:
            log.error(f"트레이더 실행 중 오류: {e}")
        finally:
            self.stop()
    
    def _start_websocket(self):
        """웹소켓 연결 시작"""
        try:
            websocket_url = "wss://api.upbit.com/websocket/v1"
            self.ws = websocket.WebSocketApp(
                websocket_url,
                on_open=self._on_websocket_open,
                on_message=self._on_websocket_message,
                on_error=self._on_websocket_error,
                on_close=self._on_websocket_close
            )
            
            # 별도 스레드에서 웹소켓 실행
            ws_thread = threading.Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            log.info("웹소켓 연결 시작")
            
        except Exception as e:
            log.error(f"웹소켓 시작 중 오류: {e}")
    
    def _on_websocket_open(self, ws):
        """웹소켓 연결 성공"""
        log.info("업비트 웹소켓 연결 성공")
        
        # 분봉 데이터 구독
        subscribe_msg = [
            {"ticket": "crypto_trader"},
            {
                "type": "ticker",  # 현재가 정보
                "codes": self.markets
            }
        ]
        
        ws.send(json.dumps(subscribe_msg))
        log.info(f"구독 시작: {self.markets}")
    
    def _on_websocket_message(self, ws, message):
        """웹소켓 메시지 수신"""
        try:
            # 바이너리 데이터 디코딩
            if isinstance(message, bytes):
                try:
                    # 압축된 데이터 시도
                    message = zlib.decompress(message).decode('utf-8')
                except zlib.error:
                    # 압축되지 않은 데이터
                    message = message.decode('utf-8')
            
            data = json.loads(message)
            market = data.get('code')
            
            # 웹소켓 데이터 로깅
            if market in self.markets:
                current_price = data.get('trade_price')
                timestamp = data.get('timestamp')
                change_rate = data.get('signed_change_rate', 0) * 100  # 변화율을 퍼센트로
                
                # print(f"🔄 [{market}] 실시간 데이터 수신:")
                # print(f"   💰 현재가: {current_price:,}원")
                # print(f"   📈 변화율: {change_rate:+.2f}%")
                # print(f"   ⏰ 시간: {timestamp}")
                # print(f"   📊 거래량: {data.get('acc_trade_volume_24h', 'N/A')}")
                # print("-" * 50)
                
                self._process_ticker_data(market, data)
                
        except Exception as e:
            log.error(f"웹소켓 메시지 처리 중 오류: {e}")
    
    def _process_ticker_data(self, market: str, ticker_data: Dict[str, Any]):
        """실시간 시세 데이터 처리 및 거래 신호 생성"""
        try:
            current_price = ticker_data.get('trade_price')
            if not current_price:
                return
            
            # 시장 데이터 업데이트
            self._update_market_data(market, ticker_data)
            
            # 매 10초마다 또는 급격한 가격 변동시에만 거래 신호 생성
            if not self._should_generate_signal(market, current_price):
                return
            
            # 모델 예측
            prediction = self._predict_action(market)
            action = prediction['action']
            confidence = prediction['confidence']
            
            # 예측 결과 저장
            self._last_predictions[market] = {
                'action': action,
                'confidence': confidence,
                'price': current_price,
                'timestamp': datetime.now().isoformat(),
                'reason': prediction.get('reason', '')
            }
            
            log.info(f"[{market}] 예측: {action} (신뢰도: {confidence:.3f}, 가격: {current_price:,}원)")
            
            # 거래 실행 조건 검사
            if action == 'HOLD':
                log.info(f"[{market}] HOLD 신호 - 거래 실행하지 않음")
                return
            
            if confidence < self.min_confidence:
                log.warning(f"[{market}] 신뢰도 부족으로 거래 스킵 - 현재: {confidence:.3f}, 최소: {self.min_confidence:.3f}")
                return
            
            log.info(f"[{market}] 거래 실행 조건 충족 - {action} 신호 (신뢰도: {confidence:.3f})")
            
            # 중복 신호 검사
            if self._should_skip_signal(market, action):
                log.warning(f"[{market}] 중복 신호로 거래 실행 스킵")
                return  # 중복 신호인 경우 주문 실행하지 않음
            
            log.info(f"[{market}] 주문 실행 시작 - {action}")
            
            order_data = {
                'action': action,
                'market': market,
                'confidence': confidence,
                'current_price': current_price,
                'amount_krw': self.trading_amount if action == 'BUY' else None,
                'timestamp': datetime.now().isoformat(),
                'reason': prediction.get('reason', '')
            }
            
            # 주문 신호 Discord 알림 전송
            self._send_discord_order_notification(order_data, "ORDER")
            
            result = self.orderer.place_order(order_data)
            
            # 주문 결과용 데이터 준비
            result_data = order_data.copy()
            
            if result:
                log.info(f"[{market}] 주문 실행 성공: {action} - {result.get('uuid')}")
                # 주문 성공시 마지막 액션 업데이트
                self._update_last_action(market, action, success=True)
                
                # 주문 성공 결과 Discord 알림
                result_data.update({
                    'success': True,
                    'uuid': result.get('uuid', 'Unknown'),
                    'error': ''
                })
                self._send_discord_order_notification(result_data, "RESULT")
                
            else:
                log.error(f"[{market}] 주문 실행 실패")
                log.error(f"[{market}] 주문 데이터: {order_data}")
                log.error(f"[{market}] 반환 결과: {result}")
                
                # 주문 실패시 마지막 액션 유지 (재시도 가능하도록)
                self._update_last_action(market, action, success=False)
                
                # 오류 메시지 수집
                error_msg = "주문 실행 실패"
                if hasattr(self.orderer, 'last_error'):
                    error_msg = str(self.orderer.last_error)
                    log.error(f"[{market}] 상세 오류: {self.orderer.last_error}")
                
                # 주문 실패 결과 Discord 알림
                result_data.update({
                    'success': False,
                    'uuid': 'Failed',
                    'error': error_msg
                })
                self._send_discord_order_notification(result_data, "RESULT")
                
                # 추가 디버깅 정보
                log.error(f"[{market}] 현재 잔고 확인 필요")
                try:
                    # 잔고 확인 로그 추가
                    if hasattr(self.orderer, 'upbit_api'):
                        balances = self.orderer.upbit_api.get_balances()
                        if balances:
                            krw_balance = 0
                            for balance in balances:
                                if balance['currency'] == 'KRW':
                                    krw_balance = float(balance['balance'])
                                    break
                            log.error(f"[{market}] 현재 KRW 잔고: {krw_balance:,.0f}원")
                        else:
                            log.error(f"[{market}] 잔고 조회 실패")
                except Exception as balance_error:
                    log.error(f"[{market}] 잔고 확인 중 오류: {balance_error}")
            
        except Exception as e:
            log.error(f"[{market}] 시세 데이터 처리 중 오류: {e}")
    
    def _update_market_data(self, market: str, ticker_data: Dict[str, Any]):
        """시장 데이터 업데이트"""
        try:
            current_time = datetime.now()
            
            # 새로운 캔들 데이터 생성
            new_candle = {
                'candle_date_time_kst': current_time,
                'trade_price': ticker_data.get('trade_price'),
                'high_price': ticker_data.get('high_price'),
                'low_price': ticker_data.get('low_price'),
                'candle_acc_trade_volume': ticker_data.get('acc_trade_volume_24h', 0),
                'timestamp': current_time.timestamp()
            }
            
            df = self.market_data.get(market, pd.DataFrame())
            
            # 새 데이터 추가
            if len(df) == 0:
                df = pd.DataFrame([new_candle])
            else:
                # 마지막 캔들과 시간 차이 확인 (1분 이상 차이나면 새 캔들)
                last_time = df.iloc[-1]['candle_date_time_kst']
                if isinstance(last_time, str):
                    last_time = pd.to_datetime(last_time)
                
                time_diff = (current_time - last_time).total_seconds()
                
                if time_diff >= 60:  # 1분 이상 차이
                    df = pd.concat([df, pd.DataFrame([new_candle])], ignore_index=True)
                else:
                    # 현재 캔들 업데이트
                    df.iloc[-1] = new_candle
            
            # 최대 200개 캔들만 유지
            if len(df) > 200:
                df = df.tail(200)
            
            # 기술적 지표 재계산
            df = self._calculate_technical_indicators(df)
            self.market_data[market] = df
            
        except Exception as e:
            log.error(f"[{market}] 시장 데이터 업데이트 중 오류: {e}")
    
    def _should_generate_signal(self, market: str, current_price: float) -> bool:
        """거래 신호 생성 여부 결정"""
        try:
            # 마지막 신호 생성 시간 체크 (10초 간격)
            current_time = time.time()
            last_signal_time = self._last_signal_times.get(market, 0)
            time_diff = current_time - last_signal_time
            
            if time_diff < 10:
                log.debug(f"[{market}] 신호 생성 스킵 - 마지막 신호로부터 {time_diff:.1f}초 경과 (최소 10초 필요)")
                return False
            
            # 마지막 신호 생성 시간 업데이트
            self._last_signal_times[market] = current_time
            log.debug(f"[{market}] 신호 생성 조건 충족 - {time_diff:.1f}초 경과")
            
            return True
            
        except Exception as e:
            log.error(f"[{market}] 신호 생성 조건 확인 중 오류: {e}")
            return False
    
    def _on_websocket_error(self, ws, error):
        """웹소켓 에러 처리"""
        log.error(f"웹소켓 에러: {error}")
    
    def _on_websocket_close(self, ws, close_status_code, close_msg):
        """웹소켓 연결 종료"""
        log.info(f"웹소켓 연결 종료: {close_status_code}, {close_msg}")
        
        # 재연결 시도
        if self.is_running:
            log.info("웹소켓 재연결 시도...")
            time.sleep(5)
            self._start_websocket()
    
    def stop(self):
        """트레이더 중지"""
        log.info("Live_Crypto_Trader 중지 중...")
        
        self.is_running = False
        self.shutdown_event.set()
        
        if self.ws:
            self.ws.close()
        
        log.info("Live_Crypto_Trader 중지 완료")
    
    def set_shutdown_event(self, event: threading.Event):
        """종료 이벤트 설정"""
        self.shutdown_event = event
    
    def get_status(self) -> Dict[str, Any]:
        """트레이더 상태 조회"""
        try:
            balance_info = self.orderer.get_balance_info()
            
            return {
                'is_running': self.is_running,
                'markets': self.markets,
                'models_loaded': list(self.models.keys()),
                'balance_info': balance_info,
                'data_status': {
                    market: len(df) for market, df in self.market_data.items()
                },
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            log.error(f"상태 조회 중 오류: {e}")
            return {'error': str(e)}

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