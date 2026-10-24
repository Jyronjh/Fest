"""LAN welcome notification and on-demand daily text summaries."""
import logging
import os
import threading
from datetime import date

import requests
import storage

MESSAGE = "YOU ARE WELCOME - PICK A SOUVENIR"
report_lock = threading.Lock()


def simulated(name):
    return os.getenv(name, "false").lower() == "true"


def welcome():
    if simulated("SIMULATE_UNOQ"):
        print(f">>> DISPLAY: {MESSAGE}", flush=True)
        return
    try:
        response = requests.post(os.environ["UNOQ_URL"], json={"type": "welcome"},
                                 headers={"X-Token": os.environ["WELCOME_TOKEN"]}, timeout=2)
        response.raise_for_status()
    except (requests.RequestException, KeyError) as exc:
        logging.warning("UNO Q welcome failed: %s", exc)


def generate_report():
    # Independent of camera processing; concurrent clicks share the current job.
    if not report_lock.acquire(blocking=False):
        return None
    try:
        day = date.today().isoformat()
        timestamps = storage.visits(day)
        text = "Summary pending"
        if simulated("SIMULATE_OLLAMA"):
            text = f"Simulation: {len(timestamps)} visitors recorded today. This is a canned report."
        else:
            prompt = (
                "Write a short plain-language attendance report, at most 120 words. "
                "Include total visitors, first and last arrival, busiest hour, quiet periods, "
                "and one sentence of observation. Use only these timestamps and count. "
                "Do not invent opening hours, identities or missing data. If empty, say no "
                "visits and that arrival times and busiest hour are unavailable.\n"
                f"Total: {len(timestamps)}\nTimestamps:\n" + "\n".join(timestamps))
            for attempt in range(2):
                try:
                    response = requests.post(
                        os.environ["OLLAMA_URL"].rstrip("/") + "/api/generate",
                        json={"model": os.environ["OLLAMA_MODEL"], "prompt": prompt,
                              "stream": False, "keep_alive": 0}, timeout=120)
                    response.raise_for_status()
                    result = response.json()["response"]
                    if not isinstance(result, str) or not result.strip():
                        raise ValueError("Empty or invalid summary")
                    text = " ".join(result.split()[:120])
                    break
                except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                    logging.warning("Ollama attempt %s failed: %s", attempt + 1, exc)
        storage.save_report(day, text)
        return storage.report(day)
    finally:
        report_lock.release()
