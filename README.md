# Visitor welcome + attendance

Four laptop modules; one SQLite file; no images saved. YuNet counts face presence, not unique people. A group counts as one visit. Enter simulation deliberately logs one visit per press; real detection uses 3-of-5 frames, 30 seconds cooldown **and** 5 continuous empty seconds. Reports run at local `REPORT_TIME` while the app is running, or on demand for today; the date picker reads past days.

**Windows / PowerShell setup** (Python 3.10+): install [Ollama](https://ollama.com/download/windows), then run:
```powershell
ollama run gemma4:e4b # Download once; exit the chat with /bye
ollama list          # Confirm gemma4:e4b is installed
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
Invoke-WebRequest 'https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx' -OutFile face_detection_yunet_2023mar.onnx
python main.py
```
Downloads are setup-only; runtime stays local. Edit only `.env` to switch components. Change `WELCOME_TOKEN` on both devices. `CAMERA_SOURCE=<video path>` uses the real detector on a clip once; leave blank for the laptop webcam. `SIMULATE_CAMERA=true` skips OpenCV and takes Enter input. `SIMULATE_UNOQ=true` prints the message. `SIMULATE_OLLAMA=true` returns a canned report. Blank `ADMIN_PIN` allows summary generation without a PIN. The app prints its detected URL; open it on a phone on the same Wi-Fi (expected `http://1.1.1.119:8000`). Set the Windows Wi-Fi profile to **Private** and allow Python through Windows Firewall on **Private** networks, TCP port 8000.

**UNO Q:** create an app in Arduino App Lab; copy `uno_q/python/main.py` into its Python editor and `uno_q/sketch/sketch.ino` into its sketch editor. Copy `.env` beside the board's Python file (only `WELCOME_TOKEN` is read). Add ArduinoGraphics through App Lab's sketch library manager if missing, then Run. The built-in matrix scrolls for 10 seconds; replace only `show_text(String)` to use an I2C LCD. In the board terminal run `hostname -I`; use its `1.1.1.x` address in `.env`'s `UNOQ_URL`, never a `172.x` address. Check from PowerShell:
```powershell
ping 1.1.1.129
Test-NetConnection -ComputerName 1.1.1.129 -Port 500
curl -Method POST http://1.1.1.129:500/welcome -Headers @{"X-Token"="change-me"}
```
Use `Invoke-WebRequest` instead of `curl` in PowerShell 7. Substitute your token. Reserve DHCP addresses for both devices; DHCP may change them. If model/pip downloads fail on this router's `1.1.1.x` range, try DNS `8.8.8.8`.

**Test in order:** (1) set `UNOQ_URL=http://127.0.0.1:500/welcome`, `SIMULATE_CAMERA=true`, `SIMULATE_UNOQ=false`; run `python fake_unoq.py` in another terminal, then `python main.py` and press Enter; (2) run `python seed_visits.py`, set `SIMULATE_OLLAMA=true`, restart and click Generate summary; (3) check phone access; (4) set `SIMULATE_CAMERA=false`; (5) restore the board URL and test the real UNO Q. Change one component at a time. Set `SIMULATE_OLLAMA=false` to use Ollama. Seeds insert 25 sample visits, including possible future times today; remove the sample SQLite file before real attendance. Run `powershell -ExecutionPolicy Bypass -File .\test.ps1` with port 500 free for the isolated no-hardware test (temporary database, mock Ollama, LAN HTTP request).

**Verification / sources:** `test.ps1` passed on 2026-10-24, including HTTP through `1.1.1.119`, gate timing, authentication and mocked Ollama failures. Board compilation/display, real webcam, phone access and real Ollama are not verified. API names checked against [Bridge](https://docs.arduino.cc/software/app-lab/bridge/bridge-api), [UNO Q matrix](https://github.com/arduino/ArduinoCore-zephyr/blob/main/libraries/Arduino_LED_Matrix/src/Arduino_LED_Matrix.h) and [ArduinoGraphics](https://github.com/arduino-libraries/ArduinoGraphics/blob/master/src/ArduinoGraphics.h). [YuNet source/license](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet); downloaded model included under `YuNet-LICENSE.txt`.
# Fest
# Fest
