import multiprocessing
import threading
import time
import logging
import signal

from core import visualizer, trader, server
from module import stock_data_manager

# INVEST_TYPE = "PROD"  # 실전투자
INVEST_TYPE = "VPS"    # 모의투자

# 각 프로세스 별 실행 여부
RUN_FLASK = True
RUN_TRADER = False

# 전역 종료 플래그
shutdown_event = threading.Event()

USE_TRADERS = [
    trader.Live_Crypto_Trader,
]

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def signal_handler(signum, frame):
    """시그널 핸들러 - Ctrl+C 처리"""
    print("\n시그널을 받았습니다. 모든 프로세스를 종료합니다...")
    shutdown_event.set()

def run_flask_server():
    """플라스크 서버 실행"""
    try:
        print("Starting Flask server...")
        # visualizer.run_server()
        server.run_server()
        
    except Exception as e:
        print(f"Flask server error: {e}")

def run_trader():
    """트레이더 앱 실행"""
    traders = []
    threads = []
    
    try:
        print("Starting Trader app...")
        for TraderClass in USE_TRADERS:
            trader_instance = TraderClass()
            
            # 트레이더에 shutdown_event 전달 (트레이더 클래스에서 지원한다면)
            if hasattr(trader_instance, 'set_shutdown_event'):
                trader_instance.set_shutdown_event(shutdown_event)
            
            trader_thread = threading.Thread(target=trader_instance.run)
            trader_thread.name = f"Trader-{TraderClass.__name__}"
            trader_thread.daemon = True  # 데몬 스레드로 설정
            
            traders.append(trader_instance)
            print(f"Starting trader: {trader_thread.name}")

            trader_thread.start()
            threads.append(trader_thread)

        # 종료 이벤트를 기다리거나 모든 스레드가 종료될 때까지 대기
        while not shutdown_event.is_set():
            # 모든 스레드가 살아있는지 확인
            alive_threads = [t for t in threads if t.is_alive()]
            if not alive_threads:
                print("모든 트레이더 스레드가 종료되었습니다.")
                break
            
            time.sleep(1)  # 1초마다 체크

    except Exception as e:
        print(f"Trader app error: {e}")
    
    finally:
        print("트레이더 종료 처리 중...")
        
        # 각 트레이더에 종료 신호 전송
        for trader_instance in traders:
            if hasattr(trader_instance, 'stop'):
                trader_instance.stop()
        
        # 모든 트레이더 스레드가 종료될 때까지 대기 (최대 10초)
        for trader_thread in threads:
            trader_thread.join(timeout=10)
            if trader_thread.is_alive():
                print(f"경고: {trader_thread.name} 스레드가 여전히 실행 중입니다.")
        
        print("All traders have finished.")


if __name__ == "__main__":
    setup_logging()
    
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 멀티프로세싱으로 필요한 모듈들을 실행
    processes = []
    
    try:
        # 플라스크 서버 프로세스
        if RUN_FLASK:
            flask_process = multiprocessing.Process(target=run_flask_server)
            flask_process.start()
            processes.append(flask_process)

        # 트레이더 앱 프로세스
        if RUN_TRADER:
            trader_process = multiprocessing.Process(target=run_trader)
            trader_process.start()
            processes.append(trader_process)
        
        print("All processes started. Press Ctrl+C to exit...")
        
        # 종료 이벤트를 기다리거나 모든 프로세스가 종료될 때까지 대기
        while not shutdown_event.is_set():
            # 모든 프로세스가 살아있는지 확인
            alive_processes = [p for p in processes if p.is_alive()]
            if not alive_processes:
                print("모든 프로세스가 종료되었습니다.")
                break
            
            time.sleep(1)  # 1초마다 체크
            
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt 받음. 종료 중...")
        shutdown_event.set()
        
    finally:
        print("모든 프로세스 종료 처리 중...")
        
        # 모든 프로세스 종료
        for process in processes:
            if process.is_alive():
                print(f"프로세스 {process.name} 종료 중...")
                process.terminate()
                process.join(timeout=10)  # 10초 대기
                
                if process.is_alive():
                    print(f"프로세스 {process.name} 강제 종료...")
                    process.kill()
                    process.join()
        
        print("All processes terminated.")