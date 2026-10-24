"""App Lab MPU: authenticated HTTP request -> one Bridge call."""
import hmac
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from arduino.app_utils import Bridge

# Copy the same .env beside this file. Only WELCOME_TOKEN is needed on the board.
env = Path(__file__).with_name(".env")
if env.exists():
    for line in env.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == "WELCOME_TOKEN":
            os.environ["WELCOME_TOKEN"] = value.strip().strip("\"'")


def call_welcome():
    # API verified against docs.arduino.cc/software/app-lab/bridge/bridge-api
    Bridge.call("welcome", timeout=1)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/welcome":
            self.send_error(404)
            return
        token = os.getenv("WELCOME_TOKEN", "")
        if not token or not hmac.compare_digest(token.encode(), self.headers.get("X-Token", "").encode()):
            self.send_error(403)
            return
        try:
            call_welcome()
        except Exception:
            logging.exception("MCU welcome failed")
            self.send_error(503, "MCU unavailable")
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ThreadingHTTPServer(("0.0.0.0", 500), Handler).serve_forever()

