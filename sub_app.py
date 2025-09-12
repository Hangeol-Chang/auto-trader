"""
Auto-trader Sub Application

main.py의 모든 기능을 Flask Blueprint로 통합 구현
- Flask 라우트들은 sub_app 인스턴스로 제공
- 백그라운드 트레이더 프로세스는 start_background_processes 함수로 제공
- visualizer 웹 서버와 trader 프로세스를 모두 관리
"""

import sys
import os
import threading
import time
import logging
import multiprocessing
import signal
from pathlib import Path
from datetime import datetime
from flask import Blueprint, jsonify, request, render_template

# 현재 모듈의 경로를 Python path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Blueprint 생성 - asset-manager와 동일한 방식으로 설정
sub_app = Blueprint('auto_trader', __name__,
                    url_prefix='/auto-trader',
                    template_folder=os.path.join(current_dir, 'web', 'templates'),
                    static_folder=os.path.join(current_dir, 'web', 'static'),
                    static_url_path='/static')

# auto-trader 모듈들 import
try:
    from core import visualizer, trader, server
    from module.stock import stock_data_manager
    # 모니터링 API 
    try:
        from core.api.monitoring_api import register_trader_instance
    except ImportError:
        register_trader_instance = lambda x: None  # 실패시 더미 함수
    
    logger = logging.getLogger('auto-trader')
    logger.info("Auto-trader 모듈 import 성공")
except ImportError as e:
    logger = logging.getLogger('auto-trader')
    logger.warning(f"Auto-trader 모듈 import 오류: {e}")
    # 필요한 경우 기본값으로 설정
    server = None
    trader = None
    visualizer = None
    stock_data_manager = None
    register_trader_instance = lambda x: None

# 설정값들 (main.py에서 가져옴)
INVEST_TYPE = "VPS"    # 모의투자
RUN_FLASK = True
RUN_TRADER = True      # 트레이더 실행 여부

# 전역 종료 플래그
shutdown_event = threading.Event()

# 트레이더 설정 (main.py와 동일)
USE_TRADERS = [
    # 새로운 하이브리드 모델 기반 트레이더
    lambda: trader.Live_Crypto_Trader(
        markets=['KRW-BTC', 'KRW-ETH'],  # 거래할 코인 목록
        interval='1m',          # 1분봉
        num_steps=5,           # LSTM 시계열 스텝
        min_confidence=0.7,    # 최소 신뢰도
        trading_amount=10000   # 거래 금액 (KRW)
    ),
] if trader else []

# 백그라운드 프로세스 관리
background_processes = []
trader_threads = []
trader_instances = []
flask_process = None

# 로깅 설정
logger = logging.getLogger(__name__)

def setup_module_logging():
    """모듈 전용 로깅 설정 (main.py 방식 적용)"""
    # logs 디렉토리 생성
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 오늘 날짜로 로그 파일명 생성
    today = datetime.now().strftime('%Y%m%d')
    log_filename = log_dir / f'trader_{today}.log'
    
    # auto-trader 전용 로그 파일
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    
    # 모듈 로거에 핸들러 추가
    module_logger = logging.getLogger('auto_trader')
    module_logger.addHandler(file_handler)
    module_logger.setLevel(logging.INFO)
    
    # 주요 모듈들의 로그 레벨 설정 (main.py와 동일)
    modules_to_log = [
        'core.trader',
        'module.upbit_api', 
        'module.crypto.crypto_orderer',
        'module.trading_executor',
        'model.predict_hybrid_signals',
        'module.discord_api'
    ]
    
    for module_name in modules_to_log:
        logger = logging.getLogger(module_name)
        logger.setLevel(logging.INFO)
    
    logger.info(f"Auto-trader 모듈 로깅 설정 완료 - 로그 파일: {log_filename}")

def signal_handler(signum, frame):
    """시그널 핸들러 - Ctrl+C 처리 (main.py와 동일)"""
    logger.info("시그널을 받았습니다. 모든 프로세스를 종료합니다...")
    shutdown_event.set()

def run_flask_server():
    """플라스크 서버 실행 (main.py와 동일)"""
    try:
        logger.info("Starting Flask server...")
        if server:
            server.run_server()
        elif visualizer:
            visualizer.run_server()
        else:
            logger.warning("서버 모듈을 사용할 수 없습니다")
    except Exception as e:
        logger.error(f"Flask server error: {e}")

def run_trader():
    """트레이더 앱 실행 (main.py와 동일)"""
    global trader_threads, trader_instances
    
    try:
        logger.info("Starting Trader app...")
        
        for trader_factory in USE_TRADERS:
            # 팩토리 함수인지 클래스인지 확인
            if callable(trader_factory) and hasattr(trader_factory, '__name__') and trader_factory.__name__ == '<lambda>':
                # 람다 함수인 경우 호출
                trader_instance = trader_factory()
            else:
                # 클래스인 경우 인스턴스 생성
                trader_instance = trader_factory()
            
            # 모니터링 API에 트레이더 등록
            register_trader_instance(trader_instance)
            
            # 트레이더에 shutdown_event 전달 (트레이더 클래스에서 지원한다면)
            if hasattr(trader_instance, 'set_shutdown_event'):
                trader_instance.set_shutdown_event(shutdown_event)
            
            trader_thread = threading.Thread(target=trader_instance.run)
            trader_thread.name = f"Trader-{trader_instance.__class__.__name__}"
            trader_thread.daemon = True  # 데몬 스레드로 설정
            
            trader_instances.append(trader_instance)
            logger.info(f"Starting trader: {trader_thread.name}")

            trader_thread.start()
            trader_threads.append(trader_thread)

        # 종료 이벤트를 기다리거나 모든 스레드가 종료될 때까지 대기
        while not shutdown_event.is_set():
            # 모든 스레드가 살아있는지 확인
            alive_threads = [t for t in trader_threads if t.is_alive()]
            if not alive_threads:
                logger.info("모든 트레이더 스레드가 종료되었습니다.")
                break
            
            time.sleep(1)  # 1초마다 체크

    except Exception as e:
        logger.error(f"Trader app error: {e}")
    
    finally:
        logger.info("트레이더 종료 처리 중...")
        
        # 각 트레이더에 종료 신호 전송
        for trader_instance in trader_instances:
            if hasattr(trader_instance, 'stop'):
                trader_instance.stop()
        
        # 모든 트레이더 스레드가 종료될 때까지 대기 (최대 10초)
        for trader_thread in trader_threads:
            trader_thread.join(timeout=10)
            if trader_thread.is_alive():
                logger.warning(f"경고: {trader_thread.name} 스레드가 여전히 실행 중입니다.")
        
        logger.info("All traders have finished.")

def start_background_processes():
    """백그라운드 프로세스 시작 (메인 앱에서 호출) - main.py와 동일한 방식"""
    global background_processes, flask_process
    
    try:
        # 로깅 설정
        setup_module_logging()
        
        # 시그널 핸들러는 메인 스레드에서만 설정 가능하므로 제거
        # signal.signal(signal.SIGINT, signal_handler)
        # signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Auto-trader 백그라운드 프로세스 시작")

        # Flask 서버 프로세스 (visualizer 웹 서버)
        if RUN_FLASK and (server or visualizer):
            flask_process = multiprocessing.Process(target=run_flask_server, name="Flask-Server")
            flask_process.start()
            background_processes.append(flask_process)
            logger.info("Flask 서버 프로세스 시작됨")

        # 트레이더 앱 프로세스
        if RUN_TRADER and trader:
            trader_process = multiprocessing.Process(target=run_trader, name="Trader-Process")
            trader_process.start()
            background_processes.append(trader_process)
            logger.info("트레이더 프로세스 시작됨")
        
        logger.info(f"총 {len(background_processes)}개 백그라운드 프로세스 시작 완료")
        
        # 모든 프로세스가 실행 중인지 주기적으로 체크
        while not shutdown_event.is_set():
            alive_processes = [p for p in background_processes if p.is_alive()]
            if not alive_processes:
                logger.info("모든 백그라운드 프로세스가 종료되었습니다.")
                break
            
            time.sleep(5)  # 5초마다 체크
        
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt 받음. 종료 중...")
        shutdown_event.set()
    except Exception as e:
        logger.error(f"백그라운드 프로세스 시작 실패: {e}")
    finally:
        stop_background_processes()

def stop_background_processes():
    """백그라운드 프로세스 중지 - main.py와 동일한 방식"""
    global background_processes, shutdown_event, flask_process
    
    logger.info("Auto-trader 백그라운드 프로세스 종료 중...")
    shutdown_event.set()
    
    # 모든 프로세스 종료
    for process in background_processes:
        if process.is_alive():
            logger.info(f"프로세스 {process.name} 종료 중...")
            process.terminate()
            process.join(timeout=10)  # 10초 대기
            
            if process.is_alive():
                logger.warning(f"프로세스 {process.name} 강제 종료...")
                process.kill()
                process.join()
    
    background_processes.clear()
    flask_process = None
    logger.info("All auto-trader processes terminated.")

def initialize_auto_trader():
    """Auto-trader 모듈 초기화"""
    try:
        setup_module_logging()
        
        # 서버 모듈 초기화 (업비트 API 키 로드 등)
        if server:
            # 업비트 API 키 로드
            if hasattr(server, 'read_upbit_keys'):
                server.read_upbit_keys()
                
            # 업비트 마켓 정보 로드
            logger.info("업비트 마켓 정보 로드 중...")
            if hasattr(server, 'load_upbit_markets') and server.load_upbit_markets():
                logger.info("마켓 정보 로드 완료. 지원 가능한 티커 수: %d", 
                           len(getattr(server, 'MARKET_INFO_CACHE', {})))
            else:
                logger.warning("마켓 정보 로드 실패. 티커 매칭이 제한될 수 있습니다.")
        
        logger.info("Auto-trader 모듈 초기화 완료")
        return True
        
    except Exception as e:
        logger.error("Auto-trader 모듈 초기화 실패: %s", e)
        return False

# ============= Blueprint 라우트 정의 =============

@sub_app.route('/')
def dashboard():
    """Auto-trader 웹 대시보드"""
    try:
        # trader_dashboard.html 사용 (url_for 방식으로 수정됨)
        return render_template('trader_dashboard.html')
        
    except Exception as e:
        logger.error(f"웹 대시보드 로드 실패: {e}")
        # 템플릿 로드 실패 시 기본 정보 제공
        trader_status = {
            "status": "error", 
            "message": "Auto-trader web dashboard load failed", 
            "module": "auto-trader",
            "error": f"웹 템플릿을 로드할 수 없음: {e}",
            "templates_dir": os.path.join(current_dir, 'web', 'templates'),
            "available_files": os.listdir(os.path.join(current_dir, 'web', 'templates')) if os.path.exists(os.path.join(current_dir, 'web', 'templates')) else []
        }
        return jsonify(trader_status)@sub_app.route('/api')
def api_dashboard():
    """Auto-trader API 정보 (기존 dashboard 기능)"""
    trader_status = {
        "status": "ok", 
        "message": "Auto-trader module is running",
        "module": "auto-trader",
        "invest_type": INVEST_TYPE,
        "features": ["crypto trading", "stock trading", "live monitoring", "web interface"],
        "trader_running": not shutdown_event.is_set(),
        "active_traders": len([t for t in trader_threads if t.is_alive()]),
        "total_traders": len(trader_threads),
        "background_processes": len([p for p in background_processes if p.is_alive()]),
        "flask_running": flask_process is not None and flask_process.is_alive() if flask_process else False
    }
    return jsonify(trader_status)

@sub_app.route('/health')
def health():
    """헬스 체크"""
    health_status = {
        "status": "ok", 
        "message": "Auto-trader module is healthy",
        "timestamp": datetime.now().isoformat(),
        "modules": {
            "trader": trader is not None,
            "server": server is not None,
            "visualizer": visualizer is not None,
            "stock_data_manager": stock_data_manager is not None
        }
    }
    return jsonify(health_status)

@sub_app.route('/status')
def status():
    """트레이더 상태 확인"""
    alive_threads = [t for t in trader_threads if t.is_alive()]
    alive_processes = [p for p in background_processes if p.is_alive()]
    
    return jsonify({
        "status": "ok",
        "trader_running": not shutdown_event.is_set(),
        "invest_type": INVEST_TYPE,
        "run_trader": RUN_TRADER,
        "run_flask": RUN_FLASK,
        "threads": {
            "total": len(trader_threads),
            "alive": len(alive_threads),
            "details": [{"name": t.name, "alive": t.is_alive()} for t in trader_threads]
        },
        "processes": {
            "total": len(background_processes),
            "alive": len(alive_processes),
            "details": [{"name": p.name, "alive": p.is_alive()} for p in background_processes]
        },
        "flask_server": {
            "enabled": RUN_FLASK,
            "running": flask_process is not None and flask_process.is_alive() if flask_process else False,
            "process_name": flask_process.name if flask_process else None
        }
    })

@sub_app.route('/start', methods=['POST'])
def start_trader():
    """트레이더 시작"""
    try:
        if not trader:
            return jsonify({"status": "error", "message": "Trader module not available"}), 400
        
        if not shutdown_event.is_set() and any(p.is_alive() for p in background_processes):
            return jsonify({"status": "error", "message": "Trader is already running"}), 400
        
        # 종료 이벤트 리셋
        shutdown_event.clear()
        
        # 새로운 스레드에서 백그라운드 프로세스 시작
        start_thread = threading.Thread(target=start_background_processes, name="ProcessStarter")
        start_thread.daemon = True
        start_thread.start()
        
        return jsonify({"status": "success", "message": "Trader started successfully"})
        
    except Exception as e:
        logger.error(f"Failed to start trader: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@sub_app.route('/stop', methods=['POST'])
def stop_trader():
    """트레이더 중지"""
    try:
        # 백그라운드 프로세스 중지
        stop_background_processes()
        
        return jsonify({"status": "success", "message": "Trader stopped successfully"})
        
    except Exception as e:
        logger.error(f"Failed to stop trader: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@sub_app.route('/restart', methods=['POST'])
def restart_trader():
    """트레이더 재시작"""
    try:
        logger.info("트레이더 재시작 요청")
        
        # 먼저 중지
        stop_background_processes()
        
        # 잠시 대기
        time.sleep(2)
        
        # 재시작
        shutdown_event.clear()
        start_thread = threading.Thread(target=start_background_processes, name="ProcessRestart")
        start_thread.daemon = True
        start_thread.start()
        
        return jsonify({"status": "success", "message": "Trader restarted successfully"})
        
    except Exception as e:
        logger.error(f"Failed to restart trader: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@sub_app.route('/config')
def get_config():
    """현재 설정 정보 반환"""
    return jsonify({
        "INVEST_TYPE": INVEST_TYPE,
        "RUN_FLASK": RUN_FLASK,
        "RUN_TRADER": RUN_TRADER,
        "USE_TRADERS": len(USE_TRADERS),
        "trader_available": trader is not None,
        "server_available": server is not None,
        "visualizer_available": visualizer is not None,
        "stock_data_manager_available": stock_data_manager is not None,
        "markets": ['KRW-BTC', 'KRW-ETH'] if USE_TRADERS else []
    })

@sub_app.route('/logs')
def get_logs():
    """최근 로그 조회"""
    try:
        log_dir = Path("logs")
        today = datetime.now().strftime('%Y%m%d')
        log_file = log_dir / f'trader_{today}.log'
        
        if not log_file.exists():
            return jsonify({"status": "error", "message": "Log file not found"}), 404
        
        # 최근 100줄만 읽기
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-100:] if len(lines) > 100 else lines
        
        return jsonify({
            "status": "success",
            "log_file": str(log_file),
            "total_lines": len(lines),
            "recent_lines": len(recent_lines),
            "logs": [line.strip() for line in recent_lines]
        })
        
    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@sub_app.route('/processes')
def get_processes():
    """현재 실행 중인 프로세스 상태 조회"""
    try:
        process_info = []
        
        for process in background_processes:
            info = {
                "name": process.name,
                "pid": process.pid if process.is_alive() else None,
                "alive": process.is_alive(),
                "exitcode": process.exitcode
            }
            process_info.append(info)
        
        return jsonify({
            "status": "success",
            "total_processes": len(background_processes),
            "alive_processes": len([p for p in background_processes if p.is_alive()]),
            "processes": process_info,
            "flask_server": {
                "running": flask_process is not None and flask_process.is_alive() if flask_process else False,
                "pid": flask_process.pid if flask_process and flask_process.is_alive() else None
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get process info: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# visualizer 모듈의 웹 라우트들 추가
@sub_app.route('/backtest')
def backtest_page():
    """백테스트 페이지"""
    try:
        # 직접 auto-trader 모듈의 backtest.html 파일을 읽어서 반환
        template_path = os.path.join(current_dir, 'web', 'templates', 'backtest.html')
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 필요한 경우 static URL 경로 수정
            html_content = html_content.replace(
                "{{ url_for('static', filename=", 
                "{{ url_for('.static', filename="
            )
            
            return html_content
        else:
            raise FileNotFoundError("Auto-trader backtest.html not found")
            
    except Exception as e:
        logger.error(f"백테스트 페이지 로드 실패: {e}")
        return jsonify({"error": "백테스트 페이지를 로드할 수 없습니다", "message": str(e), "template_path": template_path if 'template_path' in locals() else "undefined"}), 500

# API 라우트들 (visualizer에서 가져옴)
@sub_app.route('/api/stock/data')
def get_stock_data():
    """주식 데이터 API"""
    try:
        if not stock_data_manager:
            return jsonify({'error': 'stock_data_manager 모듈을 사용할 수 없습니다'}), 500
            
        stock_code = request.args.get('stock_code', '005930')
        start_date = request.args.get('start_date', '20240101')
        end_date = request.args.get('end_date', '20241231')
        
        # 주식 데이터 가져오기
        data = stock_data_manager.get_processed_data_D(
            ticker=stock_code,
            start_date=start_date,
            end_date=end_date
        )
        
        if data.empty:
            return jsonify({'error': '데이터를 찾을 수 없습니다.'}), 404
        
        # DataFrame을 JSON으로 변환
        result = {
            'stock_code': stock_code,
            'data_count': len(data),
            'data': data.to_dict('records'),
            'columns': data.columns.tolist()
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Stock data API error: {e}")
        return jsonify({'error': str(e)}), 500

@sub_app.route('/api/stock/tickers')
def get_tickers():
    """전체 티커 목록 API"""
    try:
        if not stock_data_manager:
            return jsonify({'error': 'stock_data_manager 모듈을 사용할 수 없습니다'}), 500
            
        tickers = stock_data_manager.get_full_ticker(include_screening_data=False)
        
        if tickers.empty:
            return jsonify({'error': '티커 데이터를 찾을 수 없습니다.'}), 404
        
        # 상위 100개만 반환 (성능상 이유)
        result = {
            'total_count': len(tickers),
            'data': tickers.to_dict('records')
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Tickers API error: {e}")
        return jsonify({'error': str(e)}), 500

@sub_app.route('/api/system/status')
def get_system_status():
    """시스템 상태 API"""
    try:
        status = {
            'timestamp': datetime.now().isoformat(),
            'status': 'running',
            'data_directory': os.path.abspath('data'),
            'web_directory': os.path.abspath('web'),
            'trader_running': not shutdown_event.is_set(),
            'background_processes': len([p for p in background_processes if p.is_alive()])
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"System status API error: {e}")
        return jsonify({'error': str(e)}), 500

# 백테스트 관련 API들
global backtest_trader

@sub_app.route('/api/backtest/set_strategy', methods=['POST'])
def set_backtest_strategy():
    """백테스트 전략 설정 API"""
    try:
        if not trader:
            return jsonify({'error': 'trader 모듈을 사용할 수 없습니다'}), 500
            
        data = request.get_json()
        strategy_name = data.get('strategy', 'MACD')
        
        global backtest_trader
        backtest_trader = trader.Trader("backtest")
        backtest_trader.set_strategy(strategy_name)
        
        return jsonify({'status': 'success', 'message': f'Strategy set to {strategy_name}'})
    
    except Exception as e:
        logger.error(f"Set strategy API error: {e}")
        return jsonify({'error': str(e)}), 500

@sub_app.route('/api/backtest/add_sub_strategy', methods=['POST'])
def add_backtest_sub_strategy():
    """백테스트 서브 전략 추가 API"""
    try:
        data = request.get_json()
        sub_strategy = data.get('sub_strategy', 'RSI')
        
        global backtest_trader
        if backtest_trader is None:
            raise ValueError("Backtest trader is not initialized. Please set the strategy first.")
        
        backtest_trader.add_sub_strategy(sub_strategy)
        return jsonify({'status': 'success', 'message': f'Sub strategy {sub_strategy} added'})
    
    except Exception as e:
        logger.error(f"Add sub strategy API error: {e}")
        return jsonify({'error': str(e)}), 500

@sub_app.route('/api/backtest/set_data', methods=['POST'])
def set_backtest_data():
    """백테스트 데이터 설정 API"""
    try:
        data = request.get_json()
        ticker = data.get('ticker', '005930')
        start_date = data.get('start_date', '20240101')
        end_date = data.get('end_date', '20241231')
        
        global backtest_trader
        if backtest_trader is None:
            raise ValueError("Backtest trader is not initialized. Please set the strategy first.")
        
        res = backtest_trader.set_data(ticker, start_date, end_date)
        return jsonify({'status': 'success', 'result': res})

    except Exception as e:
        logger.error(f"Set data API error: {e}")
        return jsonify({'error': str(e)}), 500

@sub_app.route('/api/backtest/run', methods=['POST'])
def run_backtest():
    """백테스트 실행 API"""
    try:
        # JSON 데이터 받기
        data = request.get_json()
        ticker = data.get('ticker', '005930')
        start_date = data.get('start_date', '20240101')
        end_date = data.get('end_date', '20241231')
        
        logger.info(f"Starting backtest for {ticker} from {start_date} to {end_date}")
        
        global backtest_trader
        if backtest_trader is None:
            raise ValueError("Backtest trader is not initialized. Please set the strategy first.")
            
        result = backtest_trader.run_backtest(ticker=ticker, start_date=start_date, end_date=end_date)

        return jsonify({
            'status': 'success',
            'result': result
        })

    except Exception as e:
        logger.error(f"Backtest API error: {e}")
        return jsonify({'error': str(e)}), 500

@sub_app.route('/api/dev/reload', methods=['POST'])
def reload_modules():
    """개발용: 모듈 리로드 API"""
    try:
        import importlib
        modules_to_reload = ['core.trader', 'module.stock.stock_data_manager']
        reloaded = []
        
        for module_name in modules_to_reload:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                reloaded.append(module_name)
        
        return jsonify({
            'status': 'success',
            'reloaded_modules': reloaded,
            'message': '모듈이 리로드되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"Module reload error: {e}")
        return jsonify({'error': str(e)}), 500
# 추가 라우트들 - server 모듈과의 통합
@sub_app.route('/web-interface')
def web_interface_status():
    """웹 인터페이스 상태 확인"""
    try:
        flask_status = {
            "enabled": RUN_FLASK,
            "server_module": server is not None,
            "visualizer_module": visualizer is not None,
            "process_running": flask_process is not None and flask_process.is_alive() if flask_process else False
        }
        
        # 웹 디렉토리 확인
        web_dirs = []
        for web_dir in ['web', 'web2']:
            full_path = os.path.join(current_dir, web_dir)
            if os.path.exists(full_path):
                web_dirs.append({
                    "name": web_dir,
                    "path": full_path,
                    "exists": True,
                    "files": len(os.listdir(full_path)) if os.path.isdir(full_path) else 0
                })
        
        return jsonify({
            "status": "success",
            "flask_server": flask_status,
            "web_directories": web_dirs,
            "server_port": 5000,  # server 모듈의 기본 포트
            "visualizer_available": visualizer is not None
        })
        
    except Exception as e:
        logger.error(f"웹 인터페이스 상태 확인 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@sub_app.route('/traders')
def get_traders_info():
    """현재 설정된 트레이더들의 정보"""
    try:
        traders_info = []
        
        for i, trader_factory in enumerate(USE_TRADERS):
            trader_info = {
                "index": i,
                "type": "lambda_factory" if hasattr(trader_factory, '__name__') and trader_factory.__name__ == '<lambda>' else "class",
                "name": f"Live_Crypto_Trader_{i}"
            }
            
            # 람다 함수인 경우 설정 정보 추출 시도
            if hasattr(trader_factory, '__name__') and trader_factory.__name__ == '<lambda>':
                try:
                    # 임시로 인스턴스를 생성하여 설정 확인 (실제 실행은 안함)
                    temp_instance = trader_factory()
                    if hasattr(temp_instance, 'markets'):
                        trader_info["markets"] = temp_instance.markets
                    if hasattr(temp_instance, 'interval'):
                        trader_info["interval"] = temp_instance.interval
                    if hasattr(temp_instance, 'trading_amount'):
                        trader_info["trading_amount"] = temp_instance.trading_amount
                    # 임시 인스턴스 정리
                    if hasattr(temp_instance, 'stop'):
                        temp_instance.stop()
                except:
                    trader_info["error"] = "설정 정보를 가져올 수 없음"
            
            traders_info.append(trader_info)
        
        return jsonify({
            "status": "success",
            "total_traders": len(USE_TRADERS),
            "traders": traders_info,
            "invest_type": INVEST_TYPE
        })
        
    except Exception as e:
        logger.error(f"트레이더 정보 조회 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 모듈 초기화 (import 시 자동 실행)
if __name__ != '__main__':
    initialize_auto_trader()

# 모듈이 직접 실행될 때 (테스트용)
if __name__ == '__main__':
    print("Auto-trader sub_app 테스트 실행")
    print("main.py와 동일한 기능을 제공하는 독립 실행 모드")
    print(f"설정: INVEST_TYPE={INVEST_TYPE}, RUN_FLASK={RUN_FLASK}, RUN_TRADER={RUN_TRADER}")
    
    try:
        # 로깅 설정
        setup_module_logging()
        
        # 독립 실행일 때만 시그널 핸들러 등록 (메인 스레드)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Auto-trader 독립 실행 모드 시작")
        logger.info(f"설정: INVEST_TYPE={INVEST_TYPE}, RUN_FLASK={RUN_FLASK}, RUN_TRADER={RUN_TRADER}")
        
        print("All processes starting. Press Ctrl+C to exit...")
        
        # main.py와 동일한 방식으로 프로세스 시작
        start_background_processes()
        
    except KeyboardInterrupt:
        logger.info("사용자에 의한 종료")
        print("\nKeyboardInterrupt 받음. 종료 중...")
    except Exception as e:
        logger.error(f"실행 중 오류: {e}")
        print(f"실행 중 오류: {e}")
    finally:
        logger.info("Auto-trader 종료")
        print("Auto-trader 종료 완료")
