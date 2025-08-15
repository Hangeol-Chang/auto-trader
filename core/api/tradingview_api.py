"""TradingView webhook API endpoints.

이 모듈은 TradingView에서 오는 웹훅과 관련된 API 엔드포인트들을 제공합니다.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, request, jsonify

# 모듈 import
sys.path.append(str(Path(__file__).parent.parent.parent))

from module.upbit_api import UpbitAPI
from module.trading_executor import TradingExecutor
from module.logging_utils import SignalLogger

log = logging.getLogger(__name__)

# TradingView API Blueprint 생성
tradingview_bp = Blueprint('tradingview', __name__, url_prefix='/api/tradingview')

# 전역 인스턴스 (실제로는 의존성 주입을 사용하는 것이 좋습니다)
upbit_api = UpbitAPI()
trading_executor = TradingExecutor(upbit_api)
signal_logger = SignalLogger()


@tradingview_bp.route("/health", methods=["GET"])
def tradingview_health():
    """TradingView API 상태 확인"""
    return jsonify({
        "status": "ok",
        "service": "tradingview-webhook-api",
        "version": "1.0.0"
    }), 200


@tradingview_bp.route("/signal-test", methods=["POST"])
def ta_signal_test():
    """TradingView webhook payload를 받아서 로그 파일에만 저장 (테스트용)

    실제 거래를 실행하지 않고 payload만 로깅합니다.
    """
    try:
        payload: Dict[str, Any] | None = None
        text_body: str | None = None

        if request.is_json:
            payload = request.get_json(silent=True)
        else:
            text_body = request.get_data(as_text=True)

        # Log to console
        if payload is not None:
            log.info("[TA-TEST] JSON payload: %s", json.dumps(payload, ensure_ascii=False))
            print("[TA-TEST] JSON payload:", json.dumps(payload, ensure_ascii=False))
            # Log to file
            signal_logger.log_ta_signal_to_file(payload, "ta-signal-test")
        else:
            log.info("[TA-TEST] Text payload: %s", text_body)
            print("[TA-TEST] Text payload:", text_body)
            # Log to file
            signal_logger.log_ta_signal_to_file(text_body or "", "ta-signal-test")

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        log.exception("Error handling /api/tradingview/signal-test: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@tradingview_bp.route("/signal", methods=["POST"])
def ta_signal():
    """TradingView에서 웹훅을 받아 업비트 매매 신호 실행
    
    메시지 형태:
    {
        "strategy": {
            "name": "SMI/RSI",
            "settings": {
                "source": "[B]",
                "parameters": "20, 20, 1.5, 14, 5, 2"
            }
        },
        "instrument": {
            "ticker": "{{ticker}}"
        },
        "order": {
            "action": "{{strategy.order.action}}",
            "quantity": "{{strategy.order.contracts}}"
        },
        "position": {
            "new_size": "{{strategy.position_size}}"
        }
    }
    """
    try:
        payload: Dict[str, Any] | None = None
        text_body: str | None = None

        if request.is_json:
            payload = request.get_json(silent=True)
        else:
            text_body = request.get_data(as_text=True)

        # 로그 출력
        if payload is not None:
            log.info("[TA] JSON payload: %s", json.dumps(payload, ensure_ascii=False))
            print("[TA] JSON payload:", json.dumps(payload, ensure_ascii=False))
            
            # 파일에 로그 저장
            signal_logger.log_ta_signal_to_file(payload, "ta-signal")
            
            # JSON 데이터에서 매매 신호 추출 및 실행
            try:
                ticker = payload.get("instrument", {}).get("ticker", "")
                action = payload.get("order", {}).get("action", "").lower()
                
                if not ticker:
                    log.warning("티커 정보가 없습니다.")
                    return jsonify({"status": "error", "message": "Missing ticker"}), 400
                
                if not action:
                    log.warning("액션 정보가 없습니다.")
                    return jsonify({"status": "error", "message": "Missing action"}), 400
                
                log.info("매매 신호 처리: 티커=%s, 액션=%s", ticker, action)
                
                if action == "buy":
                    success = trading_executor.execute_buy_signal(ticker)
                    if success:
                        return jsonify({"status": "ok", "message": f"Buy order executed for {ticker}"}), 200
                    else:
                        return jsonify({"status": "error", "message": f"Buy order failed for {ticker}"}), 500
                
                elif action == "sell":
                    success = trading_executor.execute_sell_signal(ticker)
                    if success:
                        return jsonify({"status": "ok", "message": f"Sell order executed for {ticker}"}), 200
                    else:
                        return jsonify({"status": "error", "message": f"Sell order failed for {ticker}"}), 500
                
                else:
                    log.warning("알 수 없는 액션: %s", action)
                    return jsonify({"status": "ok", "message": f"Unknown action: {action}"}), 200
                    
            except Exception as trading_error:
                log.error("매매 신호 처리 중 오류: %s", trading_error)
                return jsonify({"status": "error", "message": f"Trading error: {str(trading_error)}"}), 500
            
        else:
            log.info("[TA] Text payload: %s", text_body)
            print("[TA] Text payload:", text_body)
            # 파일에 로그 저장
            signal_logger.log_ta_signal_to_file(text_body or "", "ta-signal")

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        log.exception("Error handling /api/tradingview/signal: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@tradingview_bp.route("/webhook-config", methods=["GET"])
def get_webhook_config():
    """TradingView 웹훅 설정 가이드"""
    config = {
        "webhook_url": "https://your-domain.com/api/tradingview/signal",
        "test_webhook_url": "https://your-domain.com/api/tradingview/signal-test",
        "message_format": {
            "strategy": {
                "name": "{{strategy.order.id}}",
                "settings": {
                    "source": "[B]",
                    "parameters": "매개변수 정보"
                }
            },
            "instrument": {
                "ticker": "{{ticker}}"
            },
            "order": {
                "action": "{{strategy.order.action}}",
                "quantity": "{{strategy.order.contracts}}"
            },
            "position": {
                "new_size": "{{strategy.position_size}}"
            }
        },
        "supported_actions": ["buy", "sell"],
        "supported_tickers": "업비트에서 지원하는 모든 KRW 마켓 티커 (BTC, ETH, XRP 등)"
    }
    
    return jsonify({
        "status": "ok",
        "config": config
    }), 200


@tradingview_bp.route("/signals/history", methods=["GET"])
def get_signal_history():
    """최근 받은 TradingView 신호 내역 조회"""
    try:
        # 실제로는 signal_logger에서 로그 파일을 읽어와야 합니다.
        # 여기서는 임시 데이터 반환
        
        limit = request.args.get('limit', 10, type=int)
        signal_type = request.args.get('type', 'all')  # all, buy, sell
        
        # 임시 데이터
        signals = [
            {
                "timestamp": "2025-08-15T10:30:00Z",
                "ticker": "BTC",
                "action": "buy",
                "strategy": "RSI_STRATEGY",
                "status": "executed",
                "order_id": "order_123"
            },
            {
                "timestamp": "2025-08-15T09:15:00Z",
                "ticker": "ETH",
                "action": "sell",
                "strategy": "MA_STRATEGY",
                "status": "executed",
                "order_id": "order_122"
            },
            {
                "timestamp": "2025-08-15T08:45:00Z",
                "ticker": "XRP",
                "action": "buy",
                "strategy": "MACD_STRATEGY",
                "status": "failed",
                "error": "Insufficient balance"
            }
        ]
        
        # 필터링
        if signal_type != 'all':
            signals = [s for s in signals if s.get('action') == signal_type]
        
        # 제한
        signals = signals[:limit]
        
        return jsonify({
            "status": "ok",
            "signals": signals,
            "total_count": len(signals),
            "filters": {
                "limit": limit,
                "type": signal_type
            }
        }), 200
        
    except Exception as e:
        log.exception("Error getting signal history: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@tradingview_bp.route("/strategies", methods=["GET"])
def get_strategies():
    """현재 활성화된 TradingView 전략 목록"""
    try:
        strategies = [
            {
                "name": "RSI_STRATEGY",
                "description": "RSI 기반 매매 전략",
                "parameters": {
                    "rsi_period": 14,
                    "overbought": 70,
                    "oversold": 30
                },
                "status": "active",
                "last_signal": "2025-08-15T10:30:00Z"
            },
            {
                "name": "MA_STRATEGY",
                "description": "이동평균선 기반 매매 전략",
                "parameters": {
                    "fast_ma": 5,
                    "slow_ma": 20
                },
                "status": "active",
                "last_signal": "2025-08-15T09:15:00Z"
            },
            {
                "name": "MACD_STRATEGY",
                "description": "MACD 기반 매매 전략",
                "parameters": {
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9
                },
                "status": "inactive",
                "last_signal": "2025-08-14T16:20:00Z"
            }
        ]
        
        return jsonify({
            "status": "ok",
            "strategies": strategies,
            "active_count": len([s for s in strategies if s['status'] == 'active']),
            "total_count": len(strategies)
        }), 200
        
    except Exception as e:
        log.exception("Error getting strategies: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500
