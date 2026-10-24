"""Local substitute for the board, using the same token and endpoint."""
import hmac
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, abort, request
from notify import MESSAGE

app = Flask(__name__, static_folder=None)


@app.post("/welcome")
def welcome():
    token = os.getenv("WELCOME_TOKEN", "")
    if not token or not hmac.compare_digest(token.encode(), request.headers.get("X-Token", "").encode()):
        abort(403)
    print(f">>> DISPLAY: {MESSAGE}", flush=True)
    return {"ok": True}


if __name__ == "__main__":
    load_dotenv(Path(__file__).with_name(".env"), override=True)
    port = int(os.getenv("UNOQ_PORT", "500"))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

