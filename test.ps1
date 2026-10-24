# Isolated smoke test: no hardware, downloads, real Ollama or production data.
param([string]$Python = "$PSScriptRoot\.venv\Scripts\python.exe")
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
@'
import contextlib, io, os, tempfile, threading
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import date
import requests
from dotenv import dotenv_values
from werkzeug.serving import make_server
import main, storage, notify, web, fake_unoq

os.environ.update({k: v for k,v in dotenv_values('.env.example').items() if v is not None})
os.environ.update(SIMULATE_CAMERA='true', SIMULATE_UNOQ='false',
                  SIMULATE_OLLAMA='false', ADMIN_PIN='test-pin')
http = requests.Session()
http.trust_env = False
servers = []
def serve(app, port):
    server = make_server('0.0.0.0', port, app, threaded=True)
    servers.append(server)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server.server_port

with tempfile.TemporaryDirectory(dir='.') as tmp:
    storage.DB = Path(tmp) / 'test.sqlite3'
    storage.init()
    try:
        serve(fake_unoq.app, 500)
        os.environ['UNOQ_URL'] = 'http://127.0.0.1:500/welcome'
        assert http.post(os.environ['UNOQ_URL'], timeout=2).status_code == 403
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch('builtins.input', side_effect=['', EOFError]):
            main.camera_loop()
        assert '>>> DISPLAY: ' + notify.MESSAGE in output.getvalue()
        assert len(storage.visits(date.today().isoformat())) == 1
        print('PASS: Enter simulation -> SQLite -> authenticated fake UNO Q')

        gate = main.VisitGate()
        assert not gate.update(True, 0)
        assert not gate.update(False, 1)
        assert not gate.update(True, 2)
        assert gate.update(True, 3)
        assert not gate.update(True, 34)  # Cooldown alone is insufficient.
        for t in range(35, 41): assert not gate.update(False, t)
        assert not gate.update(True, 41)
        assert not gate.update(True, 42)
        assert gate.update(True, 43)
        for t in range(44, 50): assert not gate.update(False, t)
        assert not gate.update(True, 50)  # Empty alone is insufficient.
        gate.interrupted()
        assert not gate.update(False, 90)
        assert gate.empty_since == 90
        print('PASS: 3-of-5 gate, 30-second cooldown, 5-second empty requirement')

        ip = web.lan_ip()
        assert not ip.startswith(('127.', '172.')), 'No usable LAN IP; LAN test not verified'
        port = serve(web.create_app(f'http://{ip}:8000'), 0)
        base = f'http://{ip}:{port}'
        page = http.get(base, timeout=5)
        assert page.status_code == 200 and 'Visitor attendance' in page.text
        assert http.get(base+'/api/visits', timeout=5).json()['count'] == 1
        assert http.get(base+'/api/visits?date=bad', timeout=5).status_code == 400
        assert http.get(base+'/api/visits?date=2000-01-01', timeout=5).json()['count'] == 0
        assert http.post(base+'/api/report/generate', timeout=5).status_code == 403
        response = Mock()
        response.json.return_value = {'response': 'One visitor arrived today.'}
        with patch('notify.requests.post', return_value=response) as mocked:
            result = http.post(base+'/api/report/generate', headers={'X-Admin-Pin':'test-pin'}, timeout=5)
            assert result.json()['text'] == 'One visitor arrived today.'
            args = mocked.call_args.kwargs
            assert args['timeout'] == 120
            assert args['json']['keep_alive'] == 0 and args['json']['stream'] is False
            assert args['json']['model'] == os.environ['OLLAMA_MODEL']
        assert http.get(base+'/api/report', timeout=5).json()['text'] == 'One visitor arrived today.'
        with patch('notify.requests.post', side_effect=requests.Timeout) as mocked:
            assert notify.generate_report()['text'] == 'Summary pending'
            assert mocked.call_count == 2
            main.record_visit()  # Board failure must not undo the recorded timestamp.
        assert len(storage.visits(date.today().isoformat())) == 2
        print('PASS: LAN page and APIs, PIN, mocked Ollama, retry and offline fallbacks at '+base)
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
'@ | & $Python -
    if ($LASTEXITCODE -ne 0) { throw 'Smoke test failed.' }
} finally { Pop-Location }
