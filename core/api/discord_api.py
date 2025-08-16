"""Discord bot API endpoints.

이 모듈은 디스코드 봇과 관련된 API 엔드포인트들을 제공합니다.
"""

from __future__ import annotations

import json
import logging
import os
import requests
import sys
from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, request, jsonify

# 모듈 path 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

log = logging.getLogger(__name__)

# Discord bot API Blueprint 생성
discord_bp = Blueprint('discord', __name__, url_prefix='/api/discord')


def load_discord_config() -> Dict[str, str]:
    """discord.json 파일에서 Discord 설정 로드"""
    try:
        config_path = Path(__file__).parent.parent.parent / "private" / "discord.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                log.info("Discord 설정을 파일에서 로드했습니다: %s", config_path)
                return config
        else:
            log.warning("Discord 설정 파일이 없습니다: %s", config_path)
            return {}
    except Exception as e:
        log.error("Discord 설정 로드 중 오류: %s", e)
        return {}


# Discord 설정 로드
discord_config = load_discord_config()
DISCORD_WEBHOOK_URL = discord_config.get("DISCORD_WEBHOOK_URL", os.getenv("DISCORD_WEBHOOK_URL", ""))
DEFAULT_DISCORD_CHANNEL_ID = discord_config.get("DISCORD_CHANNEL_ID", os.getenv("DISCORD_CHANNEL_ID", ""))


def send_to_discord_webhook(message: str, webhook_url: str = None) -> bool:
    """Discord 웹훅을 통해 메시지 전송"""
    try:
        # 최신 설정 로드
        current_config = load_discord_config()
        url = webhook_url or current_config.get("DISCORD_WEBHOOK_URL", "") or DISCORD_WEBHOOK_URL
        
        if not url:
            log.warning("Discord 웹훅 URL이 설정되지 않았습니다.")
            return False
        
        # Discord 웹훅 페이로드 구성
        payload = {
            "content": message
        }
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 204:  # Discord 웹훅 성공 응답
            log.info("Discord 웹훅을 통한 메시지 전송 성공")
            return True
        else:
            log.warning("Discord 웹훅 전송 실패 (status: %s): %s", response.status_code, response.text)
            return False
    except Exception as e:
        log.error("Discord 웹훅 전송 중 오류: %s", e)
        return False


@discord_bp.route("/health", methods=["GET"])
def discord_health():
    """디스코드 봇 API 상태 확인"""
    return jsonify({
        "status": "ok",
        "service": "discord-bot-api",
        "version": "1.0.0"
    }), 200


@discord_bp.route("/config", methods=["GET"])
def get_discord_config():
    """Discord 설정 정보 조회 (민감한 정보는 마스킹)"""
    try:
        config = load_discord_config()
        
        # 웹훅 URL 마스킹 (보안)
        webhook_url = config.get("DISCORD_WEBHOOK_URL", "")
        masked_webhook = webhook_url[:50] + "***" if len(webhook_url) > 50 else "설정되지 않음"
        
        return jsonify({
            "status": "ok",
            "config": {
                "webhook_configured": bool(webhook_url),
                "webhook_url_preview": masked_webhook,
                "channel_id": config.get("DISCORD_CHANNEL_ID", "설정되지 않음"),
                "config_file_exists": bool(config)
            }
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@discord_bp.route("/test", methods=["POST"])
def test_discord_notification():
    """Discord 알림 테스트용 엔드포인트"""
    try:
        test_message = "🧪 **Discord 알림 테스트**\n✅ 웹훅이 정상적으로 작동합니다!"
        success = send_to_discord_webhook(test_message)
        
        if success:
            return jsonify({
                "status": "ok",
                "message": "Test notification sent successfully"
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to send test notification"
            }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@discord_bp.route("/commands", methods=["GET"])
def get_discord_commands():
    """사용 가능한 디스코드 명령어 목록 반환"""
    commands = {
        "trading": {
            "/balance": "현재 잔고 조회",
            "/buy <ticker> <amount>": "매수 주문",
            "/sell <ticker> <amount>": "매도 주문",
            "/positions": "현재 포지션 조회",
            "/markets": "지원 가능한 마켓 조회"
        },
        "monitoring": {
            "/status": "거래 시스템 상태 조회",
            "/logs": "최근 거래 로그 조회",
            "/alerts": "알림 설정 관리"
        },
        "analysis": {
            "/chart <ticker>": "차트 분석 정보",
            "/signals": "최근 매매 신호 조회",
            "/performance": "포트폴리오 성과 분석"
        }
    }
    
    return jsonify({
        "status": "ok",
        "commands": commands
    }), 200


@discord_bp.route("/webhook", methods=["POST"])
def discord_webhook():
    """디스코드에서 오는 웹훅 처리"""
    try:
        payload = request.get_json(silent=True)
        
        if not payload:
            return jsonify({
                "status": "error",
                "message": "No JSON payload received"
            }), 400
        
        log.info("[DISCORD] Webhook payload: %s", json.dumps(payload, ensure_ascii=False))
        
        # 디스코드 웹훅 데이터 구조 예시
        # {
        #     "user_id": "123456789",
        #     "channel_id": "987654321",
        #     "command": "balance",
        #     "parameters": {},
        #     "timestamp": "2025-08-15T10:30:00Z"
        # }
        
        user_id = payload.get("user_id")
        command = payload.get("command")
        parameters = payload.get("parameters", {})
        
        if not user_id or not command:
            return jsonify({
                "status": "error",
                "message": "Missing required fields: user_id and command"
            }), 400
        
        # 명령어 처리
        response = handle_discord_command(command, parameters, user_id)
        
        return jsonify({
            "status": "ok",
            "response": response
        }), 200
        
    except Exception as e:
        log.exception("Error handling discord webhook: %s", e)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@discord_bp.route("/reload-config", methods=["POST"])
def reload_discord_config():
    """Discord 설정 재로드"""
    try:
        global discord_config, DISCORD_WEBHOOK_URL, DEFAULT_DISCORD_CHANNEL_ID
        
        # 설정 재로드
        discord_config = load_discord_config()
        DISCORD_WEBHOOK_URL = discord_config.get("DISCORD_WEBHOOK_URL", os.getenv("DISCORD_WEBHOOK_URL", ""))
        DEFAULT_DISCORD_CHANNEL_ID = discord_config.get("DISCORD_CHANNEL_ID", os.getenv("DISCORD_CHANNEL_ID", ""))
        
        return jsonify({
            "status": "ok",
            "message": "Discord configuration reloaded successfully",
            "webhook_configured": bool(DISCORD_WEBHOOK_URL),
            "channel_configured": bool(DEFAULT_DISCORD_CHANNEL_ID)
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@discord_bp.route("/notification", methods=["POST"])
def send_discord_notification():
    """디스코드로 알림 메시지 전송"""
    try:
        payload = request.get_json(silent=True)
        
        if not payload:
            return jsonify({
                "status": "error",
                "message": "No JSON payload received"
            }), 400
        
        # 필수 필드 확인
        required_fields = ["channel_id", "message"]
        for field in required_fields:
            if field not in payload:
                return jsonify({
                    "status": "error",
                    "message": f"Missing required field: {field}"
                }), 400
        
        channel_id = payload["channel_id"]
        message = payload["message"]
        message_type = payload.get("type", "info")  # info, warning, error, success
        
        log.info("[DISCORD] Sending notification to channel %s: %s", channel_id, message)
        
        # 메시지 타입에 따른 이모지 추가
        type_emojis = {
            "success": "✅",
            "error": "❌", 
            "warning": "⚠️",
            "info": "ℹ️"
        }
        emoji = type_emojis.get(message_type, "")
        formatted_message = f"{emoji} {message}" if emoji else message
        
        # 실제 Discord 웹훅으로 메시지 전송
        success = send_to_discord_webhook(formatted_message)
        
        if success:
            return jsonify({
                "status": "ok",
                "message": "Notification sent successfully",
                "channel_id": channel_id,
                "type": message_type
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to send Discord notification"
            }), 500
        
    except Exception as e:
        log.exception("Error sending discord notification: %s", e)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@discord_bp.route("/users/<user_id>/permissions", methods=["GET"])
def get_user_permissions(user_id: str):
    """특정 사용자의 권한 조회"""
    try:
        # 실제로는 데이터베이스에서 사용자 권한을 조회해야 합니다.
        # 임시로 기본 권한 구조 반환
        permissions = {
            "user_id": user_id,
            "permissions": {
                "trading": {
                    "view_balance": True,
                    "execute_trades": False,  # 기본적으로 거래 실행은 비활성화
                    "view_positions": True,
                    "cancel_orders": False
                },
                "monitoring": {
                    "view_logs": True,
                    "view_status": True,
                    "manage_alerts": True
                },
                "admin": {
                    "manage_users": False,
                    "system_control": False
                }
            },
            "role": "viewer"  # viewer, trader, admin
        }
        
        return jsonify({
            "status": "ok",
            "permissions": permissions
        }), 200
        
    except Exception as e:
        log.exception("Error getting user permissions: %s", e)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def handle_discord_command(command: str, parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """디스코드 명령어 처리"""
    
    # 사용자 권한 확인 (실제로는 데이터베이스에서 조회)
    # 여기서는 임시로 모든 사용자에게 기본 권한 부여
    
    if command == "balance":
        return handle_balance_command(parameters, user_id)
    elif command == "buy":
        return handle_buy_command(parameters, user_id)
    elif command == "sell":
        return handle_sell_command(parameters, user_id)
    elif command == "positions":
        return handle_positions_command(parameters, user_id)
    elif command == "markets":
        return handle_markets_command(parameters, user_id)
    elif command == "status":
        return handle_status_command(parameters, user_id)
    else:
        return {
            "type": "error",
            "message": f"Unknown command: {command}",
            "available_commands": ["balance", "buy", "sell", "positions", "markets", "status"]
        }


def handle_balance_command(parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """잔고 조회 명령어 처리"""
    try:
        # 실제로는 upbit_api.get_balances()를 호출해야 합니다.
        # 여기서는 임시 데이터 반환
        return {
            "type": "success",
            "message": "잔고 조회 완료",
            "data": {
                "total_krw": "1,000,000 KRW",
                "available_krw": "500,000 KRW",
                "crypto_holdings": {
                    "BTC": "0.01 BTC (≈ 400,000 KRW)",
                    "ETH": "0.5 ETH (≈ 100,000 KRW)"
                }
            }
        }
    except Exception as e:
        return {
            "type": "error",
            "message": f"잔고 조회 중 오류가 발생했습니다: {str(e)}"
        }


def handle_buy_command(parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """매수 명령어 처리"""
    try:
        ticker = parameters.get("ticker")
        amount = parameters.get("amount")
        
        if not ticker or not amount:
            return {
                "type": "error",
                "message": "매수 명령어에는 ticker와 amount가 필요합니다. 예: /buy BTC 100000"
            }
        
        # 실제로는 trading_executor.execute_buy_signal()을 호출해야 합니다.
        return {
            "type": "success",
            "message": f"{ticker} {amount}원 매수 주문이 접수되었습니다.",
            "data": {
                "ticker": ticker,
                "amount": amount,
                "order_id": "temp_order_123"
            }
        }
    except Exception as e:
        return {
            "type": "error",
            "message": f"매수 주문 중 오류가 발생했습니다: {str(e)}"
        }


def handle_sell_command(parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """매도 명령어 처리"""
    try:
        ticker = parameters.get("ticker")
        amount = parameters.get("amount")
        
        if not ticker:
            return {
                "type": "error",
                "message": "매도 명령어에는 ticker가 필요합니다. 예: /sell BTC 또는 /sell BTC 0.01"
            }
        
        # 실제로는 trading_executor.execute_sell_signal()을 호출해야 합니다.
        return {
            "type": "success",
            "message": f"{ticker} 매도 주문이 접수되었습니다.",
            "data": {
                "ticker": ticker,
                "amount": amount or "전량",
                "order_id": "temp_order_456"
            }
        }
    except Exception as e:
        return {
            "type": "error",
            "message": f"매도 주문 중 오류가 발생했습니다: {str(e)}"
        }


def handle_positions_command(parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """포지션 조회 명령어 처리"""
    try:
        # 실제로는 현재 보유 포지션을 조회해야 합니다.
        return {
            "type": "success",
            "message": "현재 보유 포지션",
            "data": {
                "positions": [
                    {
                        "ticker": "BTC",
                        "quantity": "0.01",
                        "avg_price": "40,000,000",
                        "current_price": "42,000,000",
                        "pnl": "+50,000 KRW (+5%)"
                    },
                    {
                        "ticker": "ETH",
                        "quantity": "0.5",
                        "avg_price": "200,000",
                        "current_price": "210,000",
                        "pnl": "+5,000 KRW (+5%)"
                    }
                ],
                "total_pnl": "+55,000 KRW (+5.5%)"
            }
        }
    except Exception as e:
        return {
            "type": "error",
            "message": f"포지션 조회 중 오류가 발생했습니다: {str(e)}"
        }


def handle_markets_command(parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """마켓 조회 명령어 처리"""
    try:
        # 실제로는 upbit_api.get_available_tickers()를 호출해야 합니다.
        return {
            "type": "success",
            "message": "지원 가능한 주요 마켓",
            "data": {
                "major_markets": [
                    "BTC", "ETH", "XRP", "ADA", "DOT", "LINK", "LTC", "BCH"
                ],
                "total_markets": 200,
                "note": "전체 목록은 /markets 엔드포인트에서 확인 가능합니다."
            }
        }
    except Exception as e:
        return {
            "type": "error",
            "message": f"마켓 조회 중 오류가 발생했습니다: {str(e)}"
        }


def handle_status_command(parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """시스템 상태 조회 명령어 처리"""
    try:
        return {
            "type": "success",
            "message": "거래 시스템 상태",
            "data": {
                "server_status": "정상",
                "api_status": "연결됨",
                "last_signal": "2025-08-15 10:30:00",
                "active_strategies": ["MA_STRATEGY", "RSI_STRATEGY"],
                "uptime": "2일 3시간 45분"
            }
        }
    except Exception as e:
        return {
            "type": "error",
            "message": f"상태 조회 중 오류가 발생했습니다: {str(e)}"
        }
