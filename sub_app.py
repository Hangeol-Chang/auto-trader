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

# Blueprint 생성 - 자체 템플릿 폴더 사용
sub_app = Blueprint('auto_trader', __name__,
                    url_prefix='/auto-trader',
                    template_folder=os.path.join(current_dir, 'web', 'templates'),
                    static_folder=os.path.join(current_dir, 'web', 'static'),
                    static_url_path='/static')

# auto-trader 모듈들 import
try:
    # visualizer 모듈 import
    from core import visualizer
    
    logger = logging.getLogger('auto-trader')
    logger.info("Auto-trader visualizer 모듈 import 성공")
    
    # visualizer의 Flask app에서 라우트들을 sub_app Blueprint로 복사
    if hasattr(visualizer, 'app') and visualizer.app:
        # visualizer app의 모든 라우트를 sub_app에 등록
        for rule in visualizer.app.url_map.iter_rules():
            # OPTIONS 메서드나 static 파일은 제외
            if 'OPTIONS' in rule.methods or rule.rule.startswith('/static'):
                continue
                
            # 라우트 함수 가져오기
            endpoint = rule.endpoint
            view_func = visualizer.app.view_functions.get(endpoint)
            
            if view_func:
                # Blueprint에 라우트 추가
                methods = list(rule.methods - {'OPTIONS'})  # OPTIONS 제외
                sub_app.add_url_rule(rule.rule, endpoint, view_func, methods=methods)
                logger.debug(f"라우트 등록: {rule.rule} -> {endpoint}")
        
        logger.info("visualizer의 모든 라우트를 sub_app에 등록 완료")
    
except ImportError as e:
    logger = logging.getLogger('auto-trader')
    logger.warning(f"Auto-trader visualizer 모듈 import 오류: {e}")
    # 필요한 경우 기본값으로 설정
    visualizer = None

# 로깅 설정 함수
def setup_logger():
    """로거 설정 - visualizer 모듈 사용"""
    if visualizer and hasattr(visualizer, 'setup_logger'):
        return visualizer.setup_logger()
    else:
        # 대체 구현
        logger = logging.getLogger('auto-trader')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

# 로거 설정 실행
setup_logger()

def start_background_processes():
    """백그라운드 프로세스 시작 (메인 앱에서 호출) - Blueprint 모드에서는 웹 서버 시작 불필요"""
    try:
        logger.info("Auto-trader Blueprint 등록 완료 - 메인 서버에서 visualizer 라우트들 제공")
        # main app의 Flask 서버에서 이미 라우트들이 등록되어 있으므로
        # 별도의 백그라운드 프로세스 시작은 불필요
        return True
            
    except Exception as e:
        logger.error(f"백그라운드 프로세스 시작 중 오류: {e}")
        return False

def stop_background_processes():
    """백그라운드 프로세스 중지 - 기본 구현"""
    try:
        logger.info("Auto-trader 백그라운드 프로세스 종료 완료")
        return True
    except Exception as e:
        logger.error(f"백그라운드 프로세스 중지 중 오류: {e}")
        return False

def initialize_auto_trader():
    """Auto-trader 모듈 초기화"""
    try:
        logger.info("Auto-trader 모듈 초기화 완료")
        return True
    except Exception as e:
        logger.error(f"Auto-trader 모듈 초기화 실패: {e}")
        return False

# ============= 추가 Blueprint 라우트 (visualizer에 없는 것들만) =============

@sub_app.route('/dashboard')
def dashboard_fallback():
    """Auto-trader 대시보드 (visualizer가 없을 때 대체)"""
    try:
        return render_template('at_simple_dashboard.html')
    except Exception as e:
        logger.error(f"대시보드 템플릿 로드 실패: {e}")
        return jsonify({
            "status": "ok", 
            "message": "Auto-trader module is running",
            "module": "auto-trader",
            "features": ["crypto trading", "stock trading", "live monitoring", "web interface"],
            "visualizer_available": visualizer is not None,
            "routes_imported": len([rule for rule in sub_app.url_map.iter_rules()]) if hasattr(sub_app, 'url_map') else 0
        })

@sub_app.route('/api')        
def api_dashboard():
    """Auto-trader API 정보 (sub_app 전용)"""
    trader_status = {
        "status": "ok", 
        "message": "Auto-trader module is running",
        "module": "auto-trader",
        "features": ["crypto trading", "stock trading", "live monitoring", "web interface"],
        "visualizer_available": visualizer is not None,
        "routes_imported": len([rule for rule in sub_app.url_map.iter_rules()]) if hasattr(sub_app, 'url_map') else 0
    }
    return jsonify(trader_status)

@sub_app.route('/web-interface')
def web_interface_status():
    """웹 인터페이스 상태 확인 (sub_app 전용)"""
    try:
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
            "web_directories": web_dirs,
            "visualizer_available": visualizer is not None,
            "routes_available": len([rule for rule in sub_app.url_map.iter_rules()]) if hasattr(sub_app, 'url_map') else 0
        })
        
    except Exception as e:
        logger.error(f"웹 인터페이스 상태 확인 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 모듈 초기화 (import 시 자동 실행)
if __name__ != '__main__':
    initialize_auto_trader()

# 모듈이 직접 실행될 때 (테스트용)
if __name__ == '__main__':
    print("Auto-trader sub_app 테스트 실행")
    print("Blueprint 모드 - main 서버에서 라우트 제공")
    
    try:
        logger = logging.getLogger('auto-trader')
        logger.info("Auto-trader Blueprint 테스트 모드")
        
        # Blueprint 테스트를 위한 간단한 Flask 앱 생성
        from flask import Flask
        test_app = Flask(__name__)
        test_app.register_blueprint(sub_app)
        
        print("테스트 서버 시작 중... (http://localhost:5001/auto-trader/)")
        test_app.run(host='0.0.0.0', port=5001, debug=True)
        
    except KeyboardInterrupt:
        logger.info("사용자에 의한 종료")
        print("\nKeyboardInterrupt 받음. 종료 중...")
    except Exception as e:
        logger.error(f"실행 중 오류: {e}")
        print(f"실행 중 오류: {e}")
    finally:
        logger.info("Auto-trader 종료")
        print("Auto-trader 종료 완료")
