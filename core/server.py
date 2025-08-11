"""Simple webhook server for TradingView signals.

Exposes POST /ta-signal and prints incoming payloads.
Intended to be started from main.py via server.run_server().

Port: 443 (HTTPS if certs provided or adhoc enabled; otherwise HTTP)

Environment variables (optional):
- SSL_CERT_FILE: path to TLS certificate (PEM)
- SSL_KEY_FILE: path to TLS private key (PEM)
- USE_ADHOC_SSL: "1" to try Flask's adhoc cert (requires 'cryptography')
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from flask import Flask, request, jsonify


log = logging.getLogger(__name__)

app = Flask(__name__)

def log_ta_signal_to_file(data: Dict[str, Any] | str) -> None:
	"""Log TradingView signal data to /data/ta-signal.txt file.
	
	Args:
		data: Either JSON dict or string data from TradingView webhook
	"""
	try:
		# Create data directory if it doesn't exist
		data_dir = Path("data")
		data_dir.mkdir(exist_ok=True)
		
		# Create log file path
		log_file = data_dir / "ta-signal.txt"
		
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

"""
메세지 형태.
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
@app.route("/ta-signal-test", methods=["POST"])
def ta_signal_test():
	"""Receive TradingView webhook payload and print it.

	Accepts JSON or raw text. Returns a simple JSON ack.
	"""
	try:
		payload: Dict[str, Any] | None = None
		text_body: str | None = None

		if request.is_json:
			payload = request.get_json(silent=True)
		else:
			text_body = request.get_data(as_text=True)

		# Print in a readable way
		if payload is not None:
			log.info("[TA] JSON payload: %s", json.dumps(payload, ensure_ascii=False))
			print("[TA] JSON payload:", json.dumps(payload, ensure_ascii=False))
		else:
			log.info("[TA] Text payload: %s", text_body)
			print("[TA] Text payload:", text_body)

		return jsonify({"status": "ok"}), 200
	except Exception as e:
		log.exception("Error handling /ta-signal: %s", e)
		return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/ta-signal", methods=["POST"])
def ta_signal():
	"""Receive TradingView webhook payload and log it to file.

	Accepts JSON or raw text. Returns a simple JSON ack.
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
			log.info("[TA] JSON payload: %s", json.dumps(payload, ensure_ascii=False))
			print("[TA] JSON payload:", json.dumps(payload, ensure_ascii=False))
			# Log to file
			log_ta_signal_to_file(payload)
		else:
			log.info("[TA] Text payload: %s", text_body)
			print("[TA] Text payload:", text_body)
			# Log to file
			log_ta_signal_to_file(text_body or "")

		return jsonify({"status": "ok"}), 200
	except Exception as e:
		log.exception("Error handling /ta-signal: %s", e)
		return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/health", methods=["GET"])  # simple liveness probe
def health():
	return jsonify({"status": "up"}), 200


def _get_ssl_context():
	"""Return an SSL context tuple or 'adhoc' if configured; otherwise None.

	Priority:
	1) If SSL_CERT_FILE and SSL_KEY_FILE are set and exist, use those.
	2) If USE_ADHOC_SSL=1, try 'adhoc' (requires 'cryptography').
	3) Else return None (HTTP).
	"""
	cert = os.getenv("SSL_CERT_FILE")
	key = os.getenv("SSL_KEY_FILE")
	if cert and key and os.path.exists(cert) and os.path.exists(key):
		log.info("Using provided SSL certificate and key.")
		return cert, key

	if os.getenv("USE_ADHOC_SSL") == "1":
		try:
			# Werkzeug will lazily create an adhoc cert if 'cryptography' is available
			log.info("Using adhoc SSL certificate.")
			return "adhoc"
		except Exception as e:  # pragma: no cover - defensive
			log.warning("Failed to enable adhoc SSL (%s); falling back to HTTP.", e)

	return None


def run_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = False) -> None:
	"""Run the webhook server.

	Args:
		host: Bind address. Defaults to 0.0.0.0
		port: Port to listen on. Defaults to 5000
		debug: Flask debug mode.
	"""
	# Ensure logging is at least configured
	if not logging.getLogger().handlers:
		logging.basicConfig(level=logging.INFO)

	ssl_context = _get_ssl_context()
	scheme = "HTTPS" if ssl_context else "HTTP"
	log.info("Starting %s server on %s:%s", scheme, host, port)
	print(f"Starting {scheme} server on {host}:{port}")

	# Note: For production, consider a WSGI server (gunicorn, waitress) behind a reverse proxy.
	app.run(host=host, port=port, debug=debug, ssl_context=ssl_context, use_reloader=False)


__all__ = ["run_server", "app"]

