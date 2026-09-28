import subprocess
import sys
import time
import os
from pathlib import Path

# Enable UTF-8 encoding safely on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT_DIR = Path(__file__).resolve().parent

def main():
    print("=" * 65)
    print("[SRE-Shield] AI-Powered Incident Response Platform")
    print("=" * 65)
    print("Starting database initialization and Hindsight memory seeding...")

    # Run seed script first
    seed_cmd = [sys.executable, str(ROOT_DIR / "seed.py")]
    seed_proc = subprocess.run(seed_cmd)
    if seed_proc.returncode != 0:
        print("[Warning] Seed script returned non-zero code, continuing startup.")

    print("\n[+] Launching FastAPI Backend on http://127.0.0.1:8000 ...")
    backend_cmd = [
        sys.executable, "-m", "uvicorn", "backend.api.main:app",
        "--host", "127.0.0.1", "--port", "8000"
    ]
    backend_proc = subprocess.Popen(backend_cmd, cwd=str(ROOT_DIR))

    # Give backend a moment to bind
    time.sleep(3)

    print("[+] Launching Streamlit Dashboard on http://localhost:8501 ...")
    frontend_cmd = [
        sys.executable, "-m", "streamlit", "run", "frontend/app.py",
        "--server.port", "8501",
        "--server.headless", "true",
        "--theme.base", "dark"
    ]
    frontend_proc = subprocess.Popen(frontend_cmd, cwd=str(ROOT_DIR))

    print("\n" + "=" * 65)
    print("[SUCCESS] SRE-Shield is LIVE!")
    print("  * Frontend Dashboard : http://localhost:8501")
    print("  * Backend REST API   : http://127.0.0.1:8000")
    print("  * API Documentation  : http://127.0.0.1:8000/docs")
    print("=" * 65)
    print("Press Ctrl+C to terminate both servers.\n")

    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("Backend terminated.")
                break
            if frontend_proc.poll() is not None:
                print("Frontend terminated.")
                break
    except KeyboardInterrupt:
        print("\nStopping SRE-Shield processes...")
    finally:
        try:
            backend_proc.terminate()
            frontend_proc.terminate()
        except Exception:
            pass
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
