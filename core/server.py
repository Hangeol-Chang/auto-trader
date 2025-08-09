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
from typing import Any, Dict

from flask import Flask, request, jsonify


log = logging.getLogger(__name__)

app = Flask(__name__)

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

