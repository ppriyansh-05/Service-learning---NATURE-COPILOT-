"""
Background service supervisor for the Van Udyan platform.
Starts the FastAPI backend (port 8000) and the dashboard frontend (port 5173), restarts either one
if it exits, and writes their output to logs/. Meant to run hidden via pythonw.exe at Windows logon
(see scripts/install_autostart.ps1), but can also be run directly: python scripts/run_services.py
"""

import os
import socket
import subprocess
import sys
import time
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON = os.path.join(ROOT, "backend", "venv", "Scripts", "python.exe")
LOG_DIR = os.path.join(ROOT, "logs")
RESTART_DELAY_SECONDS = 5

SERVICES = {
    "backend": {
        "port": 8000,
        "cmd": [PYTHON, "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000"],
    },
    "frontend": {
        "port": 5173,
        "cmd": [PYTHON, os.path.join("scripts", "serve_frontend.py"), "5173"],
    },
}

# Hide child console windows when launched from pythonw.exe
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def log(message: str):
    with open(os.path.join(LOG_DIR, "supervisor.log"), "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}\n")


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def start(name: str) -> subprocess.Popen:
    svc = SERVICES[name]
    out = open(os.path.join(LOG_DIR, f"{name}.log"), "a", encoding="utf-8")
    out.write(f"\n===== {name} starting {datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
    out.flush()
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    proc = subprocess.Popen(svc["cmd"], cwd=ROOT, stdout=out, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, env=env, creationflags=CREATE_NO_WINDOW)
    log(f"started {name} (pid {proc.pid}) on port {svc['port']}")
    return proc


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    log("supervisor starting")

    procs = {}
    for name, svc in SERVICES.items():
        if port_in_use(svc["port"]):
            log(f"port {svc['port']} already in use - {name} not started (another copy may be running)")
        else:
            procs[name] = start(name)

    if not procs:
        log("nothing to supervise, exiting")
        return

    while True:
        time.sleep(RESTART_DELAY_SECONDS)
        for name, proc in list(procs.items()):
            code = proc.poll()
            if code is not None:
                log(f"{name} exited with code {code}, restarting")
                procs[name] = start(name)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        os.makedirs(LOG_DIR, exist_ok=True)
        log(f"supervisor crashed: {e!r}")
        sys.exit(1)
