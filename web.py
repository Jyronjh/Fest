"""Exactly four routes, with open viewing and an optional generation PIN."""
import hmac
import logging
import os
import socket
from datetime import date
from pathlib import Path

from flask import Flask, abort, jsonify, request
import notify
import storage


def lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))  # Select a route; no datagram is sent.
            ip = sock.getsockname()[0]
            if not ip.startswith(("172.", "127.", "0.")):
                return ip
    except OSError as exc:
        logging.warning("LAN IP route detection failed: %s", exc)
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = item[4][0]
            if not ip.startswith(("172.", "127.", "0.")):
                return ip
    except OSError:
        pass
    logging.warning("LAN address unavailable; connect Wi-Fi and restart")
    return "127.0.0.1"


def selected_day():
    value = request.args.get("date", date.today().isoformat())
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError()
    except ValueError:
        abort(400, "Use YYYY-MM-DD")
    return value


def create_app(url):
    app = Flask(__name__, static_folder=None)

    @app.get("/")
    def index():
        return (Path(__file__).with_name("index.html").read_text(encoding="utf-8")
                .replace("{{LAN_URL}}", url)
                .replace("{{TODAY}}", date.today().isoformat())
                .replace("{{PIN_REQUIRED}}", "true" if os.getenv("ADMIN_PIN") else "false"))

    @app.get("/api/visits")
    def visits():
        day = selected_day()
        timestamps = storage.visits(day)
        return jsonify(date=day, today=date.today().isoformat(), count=len(timestamps), timestamps=timestamps)

    @app.get("/api/report")
    def report():
        day = selected_day()
        return jsonify(date=day, **storage.report(day))

    @app.post("/api/report/generate")
    def generate():
        pin = os.getenv("ADMIN_PIN", "")
        if pin and not hmac.compare_digest(pin.encode(), request.headers.get("X-Admin-Pin", "").encode()):
            abort(403)
        report = notify.generate_report()
        return (jsonify(error="A summary is already being generated"), 409) if report is None else jsonify(report)

    return app
