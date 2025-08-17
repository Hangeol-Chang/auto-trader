"""Trading API endpoints.

이 모듈은 거래 관련 API 엔드포인트들을 제공합니다.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, request, jsonify

# 모듈 import
sys.path.append(str(Path(__file__).parent.parent.parent))

from module.upbit_api import UpbitAPI
from module.trading_executor import TradingExecutor
from module.kis_stock_api import KISStockAPI

log = logging.getLogger(__name__)

# Trading API Blueprint 생성
trading_bp = Blueprint('trading', __name__, url_prefix='/api/trading')

# 전역 인스턴스 (실제로는 의존성 주입을 사용하는 것이 좋습니다)
upbit_api = UpbitAPI()
trading_executor = TradingExecutor(upbit_api)
kis_stock_api = KISStockAPI(invest_type="VPS")  # 모의투자로 기본 설정
# kis_stock_api = KISStockAPI(invest_type="PROD")  # 실제 투자로 설정


@trading_bp.route("/health", methods=["GET"])
def trading_health():
    """Trading API 상태 확인"""
    return jsonify({
        "status": "ok",
        "service": "trading-api",
        "version": "1.0.0"
    }), 200


@trading_bp.route("/balance", methods=["GET"])
def get_balance():
    """업비트 잔고 조회"""
    try:
        balances = upbit_api.get_balances()
        total_balance = upbit_api.calculate_total_balance()
        
        return jsonify({
            "status": "ok", 
            "balances": balances,
            "total_balance_krw": total_balance
        }), 200
    except Exception as e:
        log.error("잔고 조회 중 오류: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@trading_bp.route("/markets", methods=["GET"])
def get_markets():
    """지원 가능한 마켓 및 티커 목록 조회"""
    try:
        available_tickers = upbit_api.get_available_tickers()
        market_details = {}
        
        # 상위 20개 주요 코인만 상세 정보 포함
        major_tickers = ['BTC', 'ETH', 'XRP', 'ADA', 'DOT', 'LINK', 'LTC', 'BCH', 'EOS', 'TRX', 
                        'ETC', 'ATOM', 'BAT', 'ENJ', 'KNC', 'MANA', 'SAND', 'AXS', 'CHZ', 'FLOW']
        
        for ticker in major_tickers:
            if ticker in upbit_api.market_info_cache:
                market_details[ticker] = upbit_api.market_info_cache[ticker]
        
        return jsonify({
            "status": "ok",
            "total_markets": len(available_tickers),
            "all_tickers": sorted(available_tickers),
            "major_markets": market_details
        }), 200
    except Exception as e:
        log.error("마켓 조회 중 오류: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@trading_bp.route("/config", methods=["GET"])
def get_trading_config():
    """현재 매매 전략 설정값 조회"""
    try:
        config = trading_executor.get_trading_config()
        return jsonify({
            "status": "ok",
            "config": config,
            "description": {
                "max_position_ratio": "각 종목 최대 비중 (전체 자산 대비)",
                "min_order_amount": "최소 주문 금액 (원)",
                "min_sell_value": "최소 매도 가치 (원)"
            }
        }), 200
    except Exception as e:
        log.error("설정 조회 중 오류: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@trading_bp.route("/config", methods=["POST"])
def update_trading_config():
    """매매 전략 설정값 업데이트"""
    try:
        payload = request.get_json(silent=True)
        
        if not payload:
            return jsonify({
                "status": "error",
                "message": "No JSON payload received"
            }), 400
        
        # 설정 업데이트 로직 (trading_executor에 메서드가 있다고 가정)
        # trading_executor.update_trading_config(payload)
        
        log.info("Trading config updated: %s", payload)
        
        return jsonify({
            "status": "ok",
            "message": "Trading configuration updated successfully",
            "updated_config": payload
        }), 200
        
    except Exception as e:
        log.error("설정 업데이트 중 오류: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@trading_bp.route("/orders", methods=["GET"])
def get_orders():
    """현재 주문 내역 조회"""
    try:
        # 실제로는 upbit_api에서 주문 내역을 가져와야 합니다.
        # orders = upbit_api.get_orders()
        
        # 임시 데이터
        orders = [
            {
                "uuid": "order_123",
                "side": "bid",  # bid: 매수, ask: 매도
                "ord_type": "limit",
                "price": "42000000",
                "state": "wait",  # wait: 대기, done: 완료, cancel: 취소
                "market": "KRW-BTC",
                "created_at": "2025-08-15T10:30:00Z",
                "volume": "0.001",
                "remaining_volume": "0.001",
                "reserved_fee": "210",
                "remaining_fee": "210",
                "paid_fee": "0",
                "locked": "42210",
                "executed_volume": "0",
                "trades_count": 0
            }
        ]
        
        return jsonify({
            "status": "ok",
            "orders": orders,
            "total_count": len(orders)
        }), 200
        
    except Exception as e:
        log.error("주문 내역 조회 중 오류: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@trading_bp.route("/orders", methods=["POST"])
def place_order():
    """새로운 주문 생성"""
    try:
        payload = request.get_json(silent=True)
        
        if not payload:
            return jsonify({
                "status": "error",
                "message": "No JSON payload received"
            }), 400
        
        # 필수 필드 확인
        required_fields = ["market", "side", "ord_type"]
        for field in required_fields:
            if field not in payload:
                return jsonify({
                    "status": "error",
                    "message": f"Missing required field: {field}"
                }), 400
        
        market = payload["market"]  # 예: KRW-BTC
        side = payload["side"]      # bid: 매수, ask: 매도
        ord_type = payload["ord_type"]  # limit, market
        
        # 주문 타입별 추가 필드 확인
        if ord_type == "limit":
            if "price" not in payload or "volume" not in payload:
                return jsonify({
                    "status": "error",
                    "message": "Limit order requires 'price' and 'volume' fields"
                }), 400
        elif ord_type == "market":
            if side == "bid" and "price" not in payload:
                return jsonify({
                    "status": "error",
                    "message": "Market buy order requires 'price' field (total KRW amount)"
                }), 400
            elif side == "ask" and "volume" not in payload:
                return jsonify({
                    "status": "error",
                    "message": "Market sell order requires 'volume' field"
                }), 400
        
        # 실제 주문 실행 (upbit_api 사용)
        # order_result = upbit_api.place_order(payload)
        
        # 임시 응답
        order_result = {
            "uuid": "temp_order_789",
            "side": side,
            "ord_type": ord_type,
            "price": payload.get("price"),
            "state": "wait",
            "market": market,
            "created_at": "2025-08-15T10:35:00Z",
            "volume": payload.get("volume"),
            "remaining_volume": payload.get("volume"),
            "reserved_fee": "0",
            "remaining_fee": "0",
            "paid_fee": "0",
            "locked": payload.get("price") or "0",
            "executed_volume": "0",
            "trades_count": 0
        }
        
        log.info("Order placed: %s", order_result)
        
        return jsonify({
            "status": "ok",
            "message": "Order placed successfully",
            "order": order_result
        }), 200
        
    except Exception as e:
        log.error("주문 생성 중 오류: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@trading_bp.route("/orders/<order_id>", methods=["DELETE"])
def cancel_order(order_id: str):
    """주문 취소"""
    try:
        # 실제로는 upbit_api에서 주문을 취소해야 합니다.
        # cancel_result = upbit_api.cancel_order(order_id)
        
        log.info("Order cancelled: %s", order_id)
        
        return jsonify({
            "status": "ok",
            "message": f"Order {order_id} cancelled successfully",
            "cancelled_order_id": order_id
        }), 200
        
    except Exception as e:
        log.error("주문 취소 중 오류: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@trading_bp.route("/positions", methods=["GET"])
def get_positions():
    """현재 보유 포지션 조회"""
    try:
        balances = upbit_api.get_balances()
        
        # KRW가 아닌 자산만 필터링하여 포지션으로 간주
        positions = []
        for balance in balances:
            if balance['currency'] != 'KRW' and float(balance['balance']) > 0:
                # 현재 가격 정보 가져오기 (실제로는 ticker API 호출)
                market = f"KRW-{balance['currency']}"
                # current_price = upbit_api.get_ticker(market)
                
                position = {
                    "currency": balance['currency'],
                    "market": market,
                    "balance": balance['balance'],
                    "locked": balance['locked'],
                    "avg_buy_price": balance.get('avg_buy_price', '0'),
                    "avg_buy_price_modified": balance.get('avg_buy_price_modified', False),
                    "unit_currency": balance['unit_currency']
                    # "current_price": current_price,
                    # "pnl": calculate_pnl(balance, current_price)
                }
                positions.append(position)
        
        return jsonify({
            "status": "ok",
            "positions": positions,
            "total_count": len(positions)
        }), 200
        
    except Exception as e:
        log.error("포지션 조회 중 오류: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@trading_bp.route("/performance", methods=["GET"])
def get_performance():
    """포트폴리오 성과 분석"""
    try:
        # 실제로는 거래 내역을 분석해서 성과를 계산해야 합니다.
        # 여기서는 임시 데이터 반환
        
        performance = {
            "total_pnl": {
                "amount": "125000",
                "percentage": "5.2"
            },
            "daily_pnl": {
                "amount": "15000",
                "percentage": "0.6"
            },
            "weekly_pnl": {
                "amount": "80000",
                "percentage": "3.2"
            },
            "monthly_pnl": {
                "amount": "125000",
                "percentage": "5.2"
            },
            "best_performer": {
                "currency": "BTC",
                "pnl": "75000",
                "percentage": "7.5"
            },
            "worst_performer": {
                "currency": "ETH",
                "pnl": "-5000",
                "percentage": "-2.1"
            },
            "win_rate": "65.5",
            "total_trades": 47,
            "winning_trades": 31,
            "losing_trades": 16
        }
        
        return jsonify({
            "status": "ok",
            "performance": performance
        }), 200
        
    except Exception as e:
        log.error("성과 분석 중 오류: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@trading_bp.route("/stock-signal", methods=["POST"])
def handle_stock_signal():
    """주식 신호 처리 - TradingView에서 오는 주식 매매 신호를 KIS API로 처리
    
    요청 형태:
    {
        "stock_code": "005930",  # 종목코드 (삼성전자)
        "action": "buy",         # 매수/매도 (buy/sell)
        "price": 65000,          # 주문가격 (지정가, 생략시 시장가)
        "quantity": 10,          # 주문수량
        "strategy": "RSI_Strategy"  # 전략명 (선택)
    }
    """
    try:
        payload = request.get_json(silent=True)
        
        if not payload:
            return jsonify({
                "status": "error",
                "message": "No JSON payload received"
            }), 400
        
        # 필수 필드 확인
        required_fields = ["stock_code", "action", "quantity"]
        for field in required_fields:
            if field not in payload:
                return jsonify({
                    "status": "error",
                    "message": f"Missing required field: {field}"
                }), 400
        
        stock_code = payload["stock_code"]
        action = payload["action"].lower()
        price = payload.get("price")  # 지정가 (선택)
        quantity = int(payload["quantity"])
        strategy = payload.get("strategy", "Unknown")
        
        # 액션 유효성 검사
        if action not in ["buy", "sell"]:
            return jsonify({
                "status": "error",
                "message": "Action must be 'buy' or 'sell'"
            }), 400
        
        # 수량 유효성 검사
        if quantity <= 0:
            return jsonify({
                "status": "error",
                "message": "Quantity must be greater than 0"
            }), 400
        
        log.info("주식 신호 처리 시작 - 종목: %s, 액션: %s, 수량: %s, 가격: %s", 
                stock_code, action, quantity, price)
        
        # KIS API를 통한 주식 주문 실행
        if action == "buy":
            result = kis_stock_api.buy_stock(stock_code, price, quantity)
        else:  # sell
            result = kis_stock_api.sell_stock(stock_code, price, quantity)
        
        if not result:
            return jsonify({
                "status": "error",
                "message": "주문 처리 중 오류가 발생했습니다"
            }), 500
        
        if result.get("success"):
            # 주문 성공
            order_type = "지정가" if price else "시장가"
            message = f"{action.upper()} 주문 성공 - {stock_code} {quantity}주 {order_type}"
            
            response_data = {
                "status": "ok",
                "message": message,
                "order_info": {
                    "stock_code": stock_code,
                    "action": action,
                    "quantity": quantity,
                    "price": price,
                    "order_type": order_type,
                    "strategy": strategy,
                    "order_no": result.get("order_no", ""),
                    "kis_message": result.get("message", "")
                }
            }
            
            log.info("주식 주문 성공 - %s", message)
            return jsonify(response_data), 200
        else:
            # 주문 실패
            error_message = result.get("error", "알 수 없는 오류")
            log.error("주식 주문 실패 - 종목: %s, 오류: %s", stock_code, error_message)
            
            return jsonify({
                "status": "error",
                "message": f"주문 실패: {error_message}",
                "order_info": {
                    "stock_code": stock_code,
                    "action": action,
                    "quantity": quantity,
                    "price": price,
                    "strategy": strategy
                },
                "error_details": result
            }), 500
            
    except ValueError as e:
        log.error("주식 신호 처리 중 입력 오류: %s", e)
        return jsonify({
            "status": "error",
            "message": f"입력 데이터 오류: {str(e)}"
        }), 400
    except Exception as e:
        log.error("주식 신호 처리 중 예상치 못한 오류: %s", e)
        return jsonify({
            "status": "error",
            "message": f"서버 오류: {str(e)}"
        }), 500


@trading_bp.route("/stock-balance", methods=["GET"])
def get_stock_balance():
    """KIS API를 통한 주식 잔고 조회"""
    try:
        result = kis_stock_api.get_stock_balance()
        
        if not result:
            return jsonify({
                "status": "error",
                "message": "잔고 조회 중 오류가 발생했습니다"
            }), 500
        
        if result.get("success"):
            return jsonify({
                "status": "ok",
                "balance_info": result.get("balances", []),
                "summary": result.get("summary", [])
            }), 200
        else:
            error_message = result.get("error", "알 수 없는 오류")
            return jsonify({
                "status": "error",
                "message": f"잔고 조회 실패: {error_message}"
            }), 500
            
    except Exception as e:
        log.error("주식 잔고 조회 중 오류: %s", e)
        return jsonify({
            "status": "error",
            "message": f"서버 오류: {str(e)}"
        }), 500


@trading_bp.route("/stock-price/<stock_code>", methods=["GET"])
def get_stock_price(stock_code: str):
    """KIS API를 통한 주식 현재가 조회"""
    try:
        if not stock_code or len(stock_code) != 6:
            return jsonify({
                "status": "error",
                "message": "종목코드는 6자리여야 합니다 (예: 005930)"
            }), 400
        
        result = kis_stock_api.get_stock_price(stock_code)
        
        if not result:
            return jsonify({
                "status": "error",
                "message": "주가 조회 중 오류가 발생했습니다"
            }), 500
        
        if result.get("success"):
            return jsonify({
                "status": "ok",
                "stock_info": {
                    "stock_code": result.get("stock_code"),
                    "current_price": result.get("current_price"),
                    "change": result.get("change"),
                    "change_rate": result.get("change_rate"),
                    "volume": result.get("volume")
                }
            }), 200
        else:
            error_message = result.get("error", "알 수 없는 오류")
            return jsonify({
                "status": "error",
                "message": f"주가 조회 실패: {error_message}"
            }), 500
            
    except Exception as e:
        log.error("주식 현재가 조회 중 오류: %s", e)
        return jsonify({
            "status": "error",
            "message": f"서버 오류: {str(e)}"
        }), 500
