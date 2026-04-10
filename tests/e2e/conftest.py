import contextlib
import csv
import os
import subprocess
import tempfile
import time

import pytest
import requests


@pytest.fixture(scope="session", autouse=True)
def live_server():
    # Use a fresh, unique DB name and port to avoid ANY conflicts
    db_path = os.path.abspath(os.path.join("tests", "data", "e2e_test.db")).replace("\\", "/")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    # Ensure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Delete if exists from previous crashed runs
    if os.path.exists(db_path):
        with contextlib.suppress(OSError):
            os.remove(db_path)

    # Create mock seed files
    with tempfile.TemporaryDirectory() as tmp_seed_dir:
        os.environ["SEED_DIR"] = tmp_seed_dir

        # Mock unita.csv
        with open(os.path.join(tmp_seed_dir, "unita.csv"), "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["UnitName", "Tipo", "Sottocampo", "Email"])
            writer.writeheader()
            writer.writerow(
                {"UnitName": "Faido", "Tipo": "Reparto", "Sottocampo": "TestCampo", "Email": "test@example.com"}
            )
            writer.writerow(
                {"UnitName": "AdminUnit", "Tipo": "Staff", "Sottocampo": "HQ", "Email": "admin@example.com"}
            )

        # Mock terreni.csv
        with open(os.path.join(tmp_seed_dir, "terreni.csv"), "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Name", "Tags", "CenterLat", "CenterLon", "Polygon", "Description", "ImageUrls"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Name": "TestTerrain",
                    "Tags": "BIVACCO,SPORT",
                    "CenterLat": "46.0",
                    "CenterLon": "9.0",
                    "Polygon": "[[46.0, 9.0], [46.1, 9.0], [46.1, 9.1], [46.0, 9.1]]",
                    "Description": "Test description",
                    "ImageUrls": "[]",
                }
            )

        # Run init_db to seed the test DB
        import sys

        python_exe = sys.executable
        result = subprocess.run(
            [python_exe, os.path.join("app", "utils", "init_db.py")], capture_output=True, text=True, env=os.environ
        )
        if result.returncode != 0:
            print("init_db.py failed!")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            result.check_returncode()

    # Start server on 8002
    proc = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8002"],
        env=os.environ,
    )

    # Wait for ready
    url = "http://127.0.0.1:8002/login"
    start_time = time.time()
    while time.time() - start_time < 15:
        try:
            res = requests.get(url)
            if res.status_code == 200:
                break
        except requests.ConnectionError:
            pass
        time.sleep(1)
    else:
        proc.kill()
        raise RuntimeError("Server did not start in time on port 8002")

    yield "http://127.0.0.1:8002"

    proc.kill()
    proc.wait()

    # Cleanup DB
    if os.path.exists(db_path):
        with contextlib.suppress(OSError):
            os.remove(db_path)
