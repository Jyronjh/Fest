"""Start the webcam worker, daily timer and small LAN server."""
import logging
import os
import threading
import time
from collections import deque
from pathlib import Path

from dotenv import load_dotenv

import notify
import storage

detector = None


def detect_person(frame) -> bool:
    # YuNet detects face presence only; no identity or images are retained.
    global detector
    import cv2
    if detector is None:
        detector = cv2.FaceDetectorYN.create(
            str(Path(__file__).with_name("face_detection_yunet_2023mar.onnx")),
            "", (640, 480), 0.8)
    _, faces = detector.detect(frame)
    return faces is not None and len(faces) > 0


class VisitGate:
    """Three of five frames; rearm only after cooldown AND continuous emptiness."""
    def __init__(self):
        self.frames = deque(maxlen=5)
        self.last = None
        self.empty_since = None

    def update(self, present, now):
        if self.last is not None:
            if present:
                self.empty_since = None
            elif self.empty_since is None:
                self.empty_since = now
            if (now - self.last >= 30 and self.empty_since is not None
                    and now - self.empty_since >= 5):
                self.last = None
                self.frames.clear()
            return False
        self.frames.append(present)
        if sum(self.frames) >= 3:
            self.last, self.empty_since = now, None
            self.frames.clear()
            return True
        return False

    def interrupted(self):
        # A missing frame is not evidence of an empty scene.
        self.frames.clear()
        self.empty_since = None


def record_visit():
    ts = storage.add_visit()  # Commit before contacting the board.
    logging.info("Visit: %s", ts)
    threading.Thread(target=notify.welcome, daemon=True).start()


def camera_loop():
    if notify.simulated("SIMULATE_CAMERA"):
        print("Simulation: press Enter to log one visit (bypasses the frame gate).", flush=True)
        while True:
            try:
                input()
            except (EOFError, OSError):
                logging.warning("Camera simulation input closed; web server remains available")
                return
            record_visit()
    gate = VisitGate()
    while True:
        cap = None
        try:
            import cv2
            source = os.getenv("CAMERA_SOURCE", "").strip()
            cap = (cv2.VideoCapture(source) if source else cv2.VideoCapture(
                int(os.getenv("CAMERA_INDEX", "0")), cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY))
            if not cap.isOpened():
                raise RuntimeError("Cannot open camera/source")
            if not source:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            # Sample clips at real-time offsets, rather than playing every frame at 3 FPS.
            started = time.monotonic()
            while True:
                tick = time.monotonic()
                if source:
                    cap.set(cv2.CAP_PROP_POS_MSEC, (tick - started) * 1000)
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError("Camera read failed or clip ended")
                present = detect_person(cv2.resize(frame, (640, 480)))
                del frame
                if gate.update(present, time.monotonic()):
                    record_visit()
                time.sleep(max(0.001, 1 / 3 - (time.monotonic() - tick)))
        except Exception as exc:
            logging.warning("Webcam unavailable: %s", exc)
            gate.interrupted()
            if os.getenv("CAMERA_SOURCE", "").strip():
                return  # A clip ends once; it must not repeat and inflate attendance.
        finally:
            if cap is not None:
                cap.release()
        time.sleep(5)


def daily_loop():
    import schedule
    try:
        schedule.every().day.at(os.getenv("REPORT_TIME", "18:00")).do(notify.generate_report)
    except Exception as exc:
        logging.warning("Daily report timer disabled: %s", exc)
        return
    while True:
        try:
            schedule.run_pending()
        except Exception:
            logging.exception("Daily report failed")
        time.sleep(1)


if __name__ == "__main__":
    load_dotenv(Path(__file__).with_name(".env"), override=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    storage.init()
    from web import create_app, lan_ip
    port = int(os.getenv("PORT", "8000"))
    url = f"http://{lan_ip()}:{port}"
    print(f"Open on any device on this network: {url}", flush=True)
    threading.Thread(target=camera_loop, daemon=True).start()
    threading.Thread(target=daily_loop, daemon=True).start()
    create_app(url).run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)
