import contextlib
import os
import subprocess
import time

import pytest
import requests


@pytest.fixture(scope="session", autouse=True)
def live_server():
    os.environ["DATABASE_URL"] = "sqlite:///./test_uat.db"

    # Run init_db to seed the test DB
    import sys

    python_exe = sys.executable
    subprocess.run([python_exe, "init_db.py"], check=True)

    # Start server
    proc = subprocess.Popen([python_exe, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"])

    # Wait for ready
    url = "http://127.0.0.1:8000/login"
    start_time = time.time()
    while time.time() - start_time < 10:
        try:
            res = requests.get(url)
            if res.status_code == 200:
                break
        except requests.ConnectionError:
            pass
        time.sleep(0.5)
    else:
        proc.kill()
        raise RuntimeError("Server did not start in time")

    yield "http://127.0.0.1:8000"

    proc.kill()
    proc.wait()

    # Cleanup DB
    if os.path.exists("test_uat.db"):
        with contextlib.suppress(OSError):
            os.remove("test_uat.db")
