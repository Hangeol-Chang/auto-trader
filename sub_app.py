"""
Auto-trader Sub Application

기존 main.py의 기능을 Flask 서브 앱으로 구현
- Flask 라우트들은 sub_app 인스턴스로 제공
- 백그라운드 트레이더 프로세스는 start_background_processes 함수로 제공
"""

import sys
import os
import threading
import time
import logging
import multiprocessing
from pathlib import Path

# 현재 모듈의 경로를 Python path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# auto-trader 모듈들 import
try:
    from core import visualizer, trader, server
    from module import stock_data_manager
except ImportError as e:
    print(f"Auto-trader 모듈 import 오류: {e}")
    # 필요한 경우 기본값으로 설정
    server = None
    trader = None

# Flask 앱 생성 (기존 server.py의 app 사용)
if server and hasattr(server, 'app'):
    sub_app = server.app
else:
    from flask import Flask
    sub_app = Flask(__name__)
    
    # 기본 라우트 추가
    @sub_app.route('/health')
    def health():
        return {"status": "ok", "message": "Auto-trader module is running"}

# 설정값들 (기존 main.py에서 가져옴)
INVEST_TYPE = "VPS"    # 모의투자
RUN_TRADER = True      # 트레이더 실행 여부

# 전역 종료 플래그
shutdown_event = threading.Event()

USE_TRADERS = [
    trader.Live_Crypto_Trader,
] if trader else []

# 로깅 설정
logger = logging.getLogger(__name__)

def setup_module_logging():
    """모듈 전용 로깅 설정"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # auto-trader 전용 로그 파일
    log_file = log_dir / "auto_trader.log"
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    
    # 모듈 로거에 핸들러 추가
    module_logger = logging.getLogger('auto_trader')
    module_logger.addHandler(file_handler)
    module_logger.setLevel(logging.INFO)
    
    logger.info("Auto-trader 모듈 로깅 설정 완료")

def initialize_auto_trader():
    """Auto-trader 모듈 초기화"""
    try:
        setup_module_logging()
        
        # 서버 모듈 초기화 (업비트 API 키 로드 등)
        if server:
            # 업비트 API 키 로드
            server.read_upbit_keys()
            
            # 업비트 마켓 정보 로드
            logger.info("업비트 마켓 정보 로드 중...")
            if server.load_upbit_markets():
                logger.info("마켓 정보 로드 완료. 지원 가능한 티커 수: %d", len(server.MARKET_INFO_CACHE))
            else:
                logger.warning("마켓 정보 로드 실패. 티커 매칭이 제한될 수 있습니다.")
        
        logger.info("Auto-trader 모듈 초기화 완료")
        return True
        
    except Exception as e:
        logger.error("Auto-trader 모듈 초기화 실패: %s", e)
        return False

def run_trader_processes():
    """트레이더 프로세스들 실행 (기존 main.py의 run_trader 함수 기반)"""
    if not USE_TRADERS:
        logger.warning("사용 가능한 트레이더가 없습니다.")
        return
    
    traders = []
    threads = []
    
    try:
        logger.info("트레이더 프로세스 시작...")
        
        for TraderClass in USE_TRADERS:
            try:
                trader_instance = TraderClass()
                
                # 트레이더에 shutdown_event 전달 (트레이더 클래스에서 지원한다면)
                if hasattr(trader_instance, 'set_shutdown_event'):
                    trader_instance.set_shutdown_event(shutdown_event)
                
                trader_thread = threading.Thread(target=trader_instance.run)
                trader_thread.name = f"Trader-{TraderClass.__name__}"
                trader_thread.daemon = True  # 데몬 스레드로 설정
                
                traders.append(trader_instance)
                logger.info("트레이더 시작: %s", trader_thread.name)

                trader_thread.start()
                threads.append(trader_thread)
                
            except Exception as e:
                logger.error("트레이더 %s 시작 실패: %s", TraderClass.__name__, e)

        # 종료 이벤트를 기다리거나 모든 스레드가 종료될 때까지 대기
        while not shutdown_event.is_set():
            # 모든 스레드가 살아있는지 확인
            alive_threads = [t for t in threads if t.is_alive()]
            if not alive_threads:
                logger.info("모든 트레이더 스레드가 종료되었습니다.")
                break
            
            time.sleep(5)  # 5초마다 체크

    except Exception as e:
        logger.error("트레이더 프로세스 실행 중 오류: %s", e)
    
    finally:
        logger.info("트레이더 종료 처리 중...")
        
        # 각 트레이더에 종료 신호 전송
        for trader_instance in traders:
            try:
                if hasattr(trader_instance, 'stop'):
                    trader_instance.stop()
            except Exception as e:
                logger.error("트레이더 종료 중 오류: %s", e)
        
        # 모든 트레이더 스레드가 종료될 때까지 대기 (최대 10초)
        for trader_thread in threads:
            try:
                trader_thread.join(timeout=10)
                if trader_thread.is_alive():
                    logger.warning("경고: %s 스레드가 여전히 실행 중입니다.", trader_thread.name)
            except Exception as e:
                logger.error("트레이더 스레드 종료 대기 중 오류: %s", e)
        
        logger.info("트레이더 프로세스 종료 완료")

def start_background_processes():
    """백그라운드 프로세스들을 시작하는 함수 (메인 앱에서 호출됨)"""
    try:
        # 모듈 초기화
        if not initialize_auto_trader():
            logger.error("Auto-trader 초기화 실패")
            return
        
        logger.info("Auto-trader 백그라운드 프로세스 시작")
        
        # 트레이더 프로세스 실행 (설정에 따라)
        if RUN_TRADER:
            run_trader_processes()
        else:
            logger.info("트레이더 실행이 비활성화되어 있습니다.")
            # 무한 대기 (서버는 계속 실행)
            while not shutdown_event.is_set():
                time.sleep(10)
        
    except Exception as e:
        logger.error("Auto-trader 백그라운드 프로세스 오류: %s", e)

def stop_background_processes():
    """백그라운드 프로세스 종료"""
    logger.info("Auto-trader 백그라운드 프로세스 종료 신호")
    shutdown_event.set()

# 모듈 상태 확인용 라우트 추가
@sub_app.route('/status')
def module_status():
    """Auto-trader 모듈 상태 조회"""
    try:
        # 트레이더 스레드 상태 확인
        trader_status = []
        current_threads = threading.enumerate()
        
        for thread in current_threads:
            if thread.name.startswith('Trader-'):
                trader_status.append({
                    "name": thread.name,
                    "alive": thread.is_alive(),
                    "daemon": thread.daemon
                })
        
        return {
            "status": "ok",
            "module": "auto-trader",
            "shutdown_event_set": shutdown_event.is_set(),
            "trader_count": len(USE_TRADERS),
            "active_traders": trader_status,
            "config": {
                "invest_type": INVEST_TYPE,
                "run_trader": RUN_TRADER
            }
        }
    except Exception as e:
        logger.error("모듈 상태 조회 오류: %s", e)
        return {"status": "error", "message": str(e)}, 500

@sub_app.route('/control/stop')
def stop_traders():
    """트레이더 프로세스 중지"""
    try:
        logger.info("트레이더 중지 요청 받음")
        stop_background_processes()
        return {"status": "ok", "message": "Stop signal sent to traders"}
    except Exception as e:
        logger.error("트레이더 중지 중 오류: %s", e)
        return {"status": "error", "message": str(e)}, 500

@sub_app.route('/control/restart')
def restart_traders():
    """트레이더 프로세스 재시작 (향후 구현 가능)"""
    return {"status": "info", "message": "Restart functionality not implemented yet"}, 501

# 기존 서버 라우트들이 이미 sub_app에 등록되어 있음:
# - /ta-signal (POST): TradingView 웹훅 수신
# - /ta-signal-test (POST): 테스트용 웹훅
# - /health (GET): 헬스 체크
# - /test-balance (GET): 업비트 잔고 조회 테스트
# - /markets (GET): 지원 마켓 목록
# - /trading-config (GET): 매매 설정 조회

# 모듈이 직접 실행될 때 (테스트용)
if __name__ == '__main__':
    print("Auto-trader sub_app 테스트 실행")
    setup_module_logging()
    
    # Flask 앱 단독 실행
    sub_app.run(host='0.0.0.0', port=5001, debug=True)
