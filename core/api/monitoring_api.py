"""
실시간 트레이딩 모니터링 API

하이브리드 모델 기반 코인 트레이더의 상태를 모니터링하는 API
"""

import json
import logging
import os
from datetime import datetime
from flask import Blueprint, jsonify, request
from typing import Dict, Any, Optional

log = logging.getLogger(__name__)

# 글로벌 트레이더 인스턴스 참조
_trader_instances = []

monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')


def register_trader_instance(trader_instance):
    """트레이더 인스턴스 등록"""
    global _trader_instances
    _trader_instances.append(trader_instance)
    log.info(f"트레이더 인스턴스 등록: {trader_instance.__class__.__name__}")


@monitoring_bp.route("/traders", methods=["GET"])
def get_traders_status():
    """모든 트레이더의 상태 조회"""
    try:
        traders_status = []
        
        for i, trader in enumerate(_trader_instances):
            if hasattr(trader, 'get_status'):
                status = trader.get_status()
                status['trader_id'] = i
                status['trader_type'] = trader.__class__.__name__
                traders_status.append(status)
            else:
                traders_status.append({
                    'trader_id': i,
                    'trader_type': trader.__class__.__name__,
                    'status': 'unknown',
                    'error': 'Status method not available'
                })
        
        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "total_traders": len(traders_status),
            "traders": traders_status
        }), 200
        
    except Exception as e:
        log.error(f"트레이더 상태 조회 중 오류: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@monitoring_bp.route("/traders/<int:trader_id>", methods=["GET"])
def get_trader_status(trader_id: int):
    """특정 트레이더의 상세 상태 조회"""
    try:
        if trader_id >= len(_trader_instances):
            return jsonify({
                "status": "error",
                "message": f"Trader ID {trader_id} not found"
            }), 404
        
        trader = _trader_instances[trader_id]
        
        if hasattr(trader, 'get_status'):
            status = trader.get_status()
            status['trader_id'] = trader_id
            status['trader_type'] = trader.__class__.__name__
            
            return jsonify({
                "status": "ok",
                "trader": status
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Status method not available"
            }), 400
            
    except Exception as e:
        log.error(f"트레이더 {trader_id} 상태 조회 중 오류: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@monitoring_bp.route("/traders/<int:trader_id>/markets", methods=["GET"])
def get_trader_markets(trader_id: int):
    """트레이더가 거래하는 마켓 목록 조회"""
    try:
        if trader_id >= len(_trader_instances):
            return jsonify({
                "status": "error",
                "message": f"Trader ID {trader_id} not found"
            }), 404
        
        trader = _trader_instances[trader_id]
        
        markets_info = []
        if hasattr(trader, 'markets'):
            for market in trader.markets:
                market_info = {
                    'market': market,
                    'has_model': market in getattr(trader, 'models', {}),
                    'data_length': len(getattr(trader, 'market_data', {}).get(market, [])),
                }
                
                # 최근 예측 결과가 있다면 추가
                if hasattr(trader, '_last_predictions') and market in trader._last_predictions:
                    market_info['last_prediction'] = trader._last_predictions[market]
                
                markets_info.append(market_info)
        
        return jsonify({
            "status": "ok",
            "trader_id": trader_id,
            "markets": markets_info
        }), 200
        
    except Exception as e:
        log.error(f"트레이더 {trader_id} 마켓 정보 조회 중 오류: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@monitoring_bp.route("/traders/<int:trader_id>/balance", methods=["GET"])
def get_trader_balance(trader_id: int):
    """트레이더의 잔고 정보 조회"""
    try:
        if trader_id >= len(_trader_instances):
            return jsonify({
                "status": "error",
                "message": f"Trader ID {trader_id} not found"
            }), 404
        
        trader = _trader_instances[trader_id]
        
        if hasattr(trader, 'orderer') and hasattr(trader.orderer, 'get_balance_info'):
            balance_info = trader.orderer.get_balance_info()
            
            return jsonify({
                "status": "ok",
                "trader_id": trader_id,
                "balance": balance_info
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Balance information not available"
            }), 400
            
    except Exception as e:
        log.error(f"트레이더 {trader_id} 잔고 조회 중 오류: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@monitoring_bp.route("/traders/<int:trader_id>/control", methods=["POST"])
def control_trader(trader_id: int):
    """트레이더 제어 (시작/중지/설정 변경)"""
    try:
        if trader_id >= len(_trader_instances):
            return jsonify({
                "status": "error",
                "message": f"Trader ID {trader_id} not found"
            }), 404
        
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({
                "status": "error",
                "message": "No JSON payload received"
            }), 400
        
        trader = _trader_instances[trader_id]
        action = payload.get('action')
        
        if action == 'stop':
            if hasattr(trader, 'stop'):
                trader.stop()
                return jsonify({
                    "status": "ok",
                    "message": f"Trader {trader_id} stopped"
                }), 200
            else:
                return jsonify({
                    "status": "error",
                    "message": "Stop method not available"
                }), 400
                
        elif action == 'update_config':
            config = payload.get('config', {})
            
            # 설정 업데이트 로직
            updated_fields = []
            
            if 'min_confidence' in config and hasattr(trader, 'min_confidence'):
                trader.min_confidence = float(config['min_confidence'])
                updated_fields.append('min_confidence')
            
            if 'trading_amount' in config and hasattr(trader, 'trading_amount'):
                trader.trading_amount = int(config['trading_amount'])
                updated_fields.append('trading_amount')
            
            return jsonify({
                "status": "ok",
                "message": f"Configuration updated: {', '.join(updated_fields)}"
            }), 200
            
        else:
            return jsonify({
                "status": "error",
                "message": f"Unknown action: {action}"
            }), 400
            
    except Exception as e:
        log.error(f"트레이더 {trader_id} 제어 중 오류: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@monitoring_bp.route("/system", methods=["GET"])
def get_system_status():
    """시스템 전체 상태 조회"""
    try:
        system_info = {"message": "System monitoring requires psutil package"}
        process_info = {"pid": os.getpid()}
        
        # psutil이 설치되어 있으면 시스템 정보 수집
        try:
            import psutil
            
            # 시스템 리소스 정보
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 프로세스 정보
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info()
            
            system_info = {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                }
            }
            
            process_info = {
                "pid": os.getpid(),
                "memory": {
                    "rss": process_memory.rss,
                    "vms": process_memory.vms
                },
                "cpu_percent": process.cpu_percent(),
                "num_threads": process.num_threads()
            }
            
        except ImportError:
            log.warning("psutil not available - limited system information")
        
        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "system": system_info,
            "process": process_info,
            "traders": {
                "total": len(_trader_instances),
                "running": sum(1 for t in _trader_instances if getattr(t, 'is_running', False))
            }
        }), 200
        
    except Exception as e:
        log.error(f"시스템 상태 조회 중 오류: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@monitoring_bp.route("/logs", methods=["GET"])
def get_recent_logs():
    """최근 로그 조회"""
    try:
        # 로그 파일에서 최근 로그 읽기
        log_dir = "logs"
        today = datetime.now().strftime("%Y%m%d")
        log_file = f"{log_dir}/server_{today}.log"
        
        lines = request.args.get('lines', 100, type=int)
        level = request.args.get('level', 'all').upper()
        
        logs = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                for line in recent_lines:
                    line = line.strip()
                    if line and (level == 'ALL' or level in line):
                        logs.append(line)
        
        return jsonify({
            "status": "ok",
            "total_lines": len(logs),
            "logs": logs
        }), 200
        
    except Exception as e:
        log.error(f"로그 조회 중 오류: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
