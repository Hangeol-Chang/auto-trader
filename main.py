import multiprocessing
import time
import logging

from module import visualizer
from module import trader

# INVEST_TYPE = "PROD"  # 실전투자
INVEST_TYPE = "VPS"    # 모의투자

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def run_flask_server():
    """플라스크 서버 실행"""
    try:
        print("Starting Flask server...")
        visualizer.run_server()
    except Exception as e:
        print(f"Flask server error: {e}")

def run_trader():
    """트레이더 앱 실행"""
    try:
        print("Starting Trader app...")
        trader.run_trader()
    except Exception as e:
        print(f"Trader app error: {e}")

if __name__ == "__main__":
    setup_logging()
    
    # 멀티프로세싱으로 필요한 모듈들을 실행
    processes = []
    
    try:
        # 플라스크 서버 프로세스
        flask_process = multiprocessing.Process(target=run_flask_server)
        flask_process.start()
        processes.append(flask_process)
        
        # 트레이더 앱 프로세스  
        # trader_process = multiprocessing.Process(target=run_trader)
        # trader_process.start()
        # processes.append(trader_process)
        
        print("All processes started. Press Ctrl+C to exit...")
        
        # 모든 프로세스가 실행될 때까지 대기
        for process in processes:
            process.join()
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        
        # 모든 프로세스 종료
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()
        
        print("All processes terminated.")