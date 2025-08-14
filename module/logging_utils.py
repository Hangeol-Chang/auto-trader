"""로깅 관련 유틸리티 모듈.

TradingView 신호 로깅 및 서버 로깅 설정을 처리합니다.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Union

log = logging.getLogger(__name__)

class SignalLogger:
    """신호 로깅 클래스"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
    
    def log_ta_signal_to_file(self, data: Union[Dict[str, Any], str], endpoint: str = "ta-signal") -> None:
        """Log TradingView signal data to appropriate file based on endpoint.
        
        Args:
            data: Either JSON dict or string data from TradingView webhook
            endpoint: The endpoint name to determine the log file (ta-signal or ta-signal-test)
        """
        try:
            # Create log file path based on endpoint
            log_file = self.data_dir / (endpoint + ".txt")

            # Get current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Format the log entry
            if isinstance(data, dict):
                # JSON data - parse key fields
                strategy_name = data.get("strategy", {}).get("name", "Unknown")
                ticker = data.get("instrument", {}).get("ticker", "Unknown")
                action = data.get("order", {}).get("action", "Unknown")
                quantity = data.get("order", {}).get("quantity", "Unknown")
                position_size = data.get("position", {}).get("new_size", "Unknown")
                
                log_entry = f"[{timestamp}] JSON | Strategy: {strategy_name} | Ticker: {ticker} | Action: {action} | Qty: {quantity} | Position: {position_size} | Raw: {json.dumps(data, ensure_ascii=False)}"
            else:
                # Plain text data
                log_entry = f"[{timestamp}] TEXT | Data: {data}"
            
            # Append to file
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
                
            log.info("Signal logged to %s", log_file)
            
        except Exception as e:
            log.error("Failed to log signal to file: %s", e)

def setup_server_logging(log_dir: str = "logs") -> None:
    """서버 로깅 설정
    
    Args:
        log_dir: 로그 파일을 저장할 디렉토리
    """
    # 로깅 설정 개선 - 파일과 콘솔 모두에 로그 출력
    if not logging.getLogger().handlers:
        # 로그 디렉토리 생성
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        # 로그 파일 경로
        log_file = log_path / f"server_{datetime.now().strftime('%Y%m%d')}.log"
        
        # 로깅 포맷 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 파일 핸들러 (로그 파일에 저장)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # 콘솔 핸들러 (터미널에 출력)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # 루트 로거에 핸들러 추가
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        log.info("로깅이 설정되었습니다. 로그 파일: %s", log_file)
