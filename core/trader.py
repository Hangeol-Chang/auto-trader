
"""
자동 트레이딩 모듈
"""

import os
import time
import logging
import json
from datetime import datetime, timedelta
from module import stock_data_manager

STATE_DATA_DIR = "data/state"

logger = logging.getLogger(__name__)

class AutoTrader:
    """자동 트레이더 클래스"""
    
    def __init__(self, config=None):
        self.config = config or self._load_default_config()
        self.state_file = os.path.join(STATE_DATA_DIR, "trader_state.json")
        self.is_running = False
        self._ensure_state_directory()
        
    def _load_default_config(self):
        """기본 설정 로드"""
        return {
            'target_stocks': ['005930', '000660', '035420'],  # 삼성전자, SK하이닉스, NAVER
            'balance': 10000000,  # 1천만원
            'max_position_per_stock': 0.3,  # 종목당 최대 30%
            'trading_interval': 60,  # 60초마다 체크
            'stop_loss_ratio': 0.05,  # 5% 손절
            'take_profit_ratio': 0.1,  # 10% 익절
            'analysis_period': 30  # 30일 분석 기간
        }
    
    def _ensure_state_directory(self):
        """상태 디렉토리 생성"""
        if not os.path.exists(STATE_DATA_DIR):
            os.makedirs(STATE_DATA_DIR)
    
    def save_state(self, state_data):
        """상태 저장"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2, default=str)
            logger.info("Trader state saved")
        except Exception as e:
            logger.error(f"Failed to save trader state: {e}")
    
    def load_state(self):
        """상태 로드"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                logger.info("Trader state loaded")
                return state_data
            else:
                logger.info("No existing trader state found, creating new one")
                return self._create_initial_state()
        except Exception as e:
            logger.error(f"Failed to load trader state: {e}")
            return self._create_initial_state()
    
    def _create_initial_state(self):
        """초기 상태 생성"""
        return {
            'balance': self.config['balance'],
            'positions': {},  # 보유 포지션
            'trade_history': [],  # 거래 내역
            'last_update': datetime.now().isoformat(),
            'status': 'initialized'
        }
    
    def analyze_stock(self, stock_code):
        """종목 분석"""
        try:
            # 최근 30일 데이터 가져오기
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=self.config['analysis_period'])).strftime('%Y%m%d')
            
            data = stock_data_manager.get_processed_data_D(
                itm_no=stock_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if data.empty:
                logger.warning(f"No data available for stock {stock_code}")
                return None
            
            # 최신 데이터
            latest = data.iloc[-1]
            
            # 간단한 분석 로직
            analysis = {
                'stock_code': stock_code,
                'current_price': latest.get('close', 0),
                'macd': latest.get('macd', 0),
                'macd_signal': latest.get('macd_signal', 0),
                'macd_histogram': latest.get('macd_histogram', 0),
                'sma_short': latest.get('sma_short', 0),
                'sma_long': latest.get('sma_long', 0),
                'analysis_time': datetime.now().isoformat()
            }
            
            # 매매 신호 판단 (매우 기초적인 로직)
            signal = 'hold'
            if analysis['macd'] > analysis['macd_signal'] and analysis['macd_histogram'] > 0:
                if analysis['current_price'] > analysis['sma_short']:
                    signal = 'buy'
            elif analysis['macd'] < analysis['macd_signal'] and analysis['macd_histogram'] < 0:
                if analysis['current_price'] < analysis['sma_short']:
                    signal = 'sell'
            
            analysis['signal'] = signal
            
            logger.info(f"Stock {stock_code} analysis: {signal}, price: {analysis['current_price']}")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze stock {stock_code}: {e}")
            return None
    
    def process_trading_decision(self, analysis):
        """거래 결정 처리"""
        try:
            # 실제 거래는 모의로 처리 (여기서는 로깅만)
            stock_code = analysis['stock_code']
            signal = analysis['signal']
            price = analysis['current_price']
            
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'stock_code': stock_code,
                'signal': signal,
                'price': price,
                'executed': False,  # 실제로는 거래소 API를 통해 처리
                'reason': 'simulated_trade'
            }
            
            if signal == 'buy':
                logger.info(f"BUY signal for {stock_code} at {price}")
            elif signal == 'sell':
                logger.info(f"SELL signal for {stock_code} at {price}")
            else:
                logger.info(f"HOLD signal for {stock_code} at {price}")
            
            return trade_record
            
        except Exception as e:
            logger.error(f"Failed to process trading decision: {e}")
            return None
    
    def run_trading_cycle(self):
        """한 번의 트레이딩 사이클 실행"""
        try:
            logger.info("Starting trading cycle...")
            
            state = self.load_state()
            state['last_update'] = datetime.now().isoformat()
            state['status'] = 'analyzing'
            
            # 각 종목에 대해 분석 및 거래 결정
            for stock_code in self.config['target_stocks']:
                logger.info(f"Analyzing stock: {stock_code}")
                
                analysis = self.analyze_stock(stock_code)
                if analysis:
                    trade_record = self.process_trading_decision(analysis)
                    if trade_record:
                        state['trade_history'].append(trade_record)
                
                # API 호출 간격 조절
                time.sleep(1)
            
            state['status'] = 'waiting'
            self.save_state(state)
            
            logger.info("Trading cycle completed")
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
    
    def start(self):
        """트레이더 시작"""
        self.is_running = True
        logger.info("Auto Trader started")
        
        while self.is_running:
            try:
                self.run_trading_cycle()
                time.sleep(self.config['trading_interval'])
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                self.stop()
            except Exception as e:
                logger.error(f"Unexpected error in trader loop: {e}")
                time.sleep(10)  # 오류 발생시 10초 대기 후 재시도
    
    def stop(self):
        """트레이더 중지"""
        self.is_running = False
        state = self.load_state()
        state['status'] = 'stopped'
        state['last_update'] = datetime.now().isoformat()
        self.save_state(state)
        logger.info("Auto Trader stopped")

def run_trader():
    """트레이더 실행"""
    try:
        trader = AutoTrader()
        trader.start()
    except Exception as e:
        logger.error(f"Failed to run trader: {e}")
        raise