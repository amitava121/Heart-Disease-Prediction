#!/usr/bin/env python3
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
PROJECT_ROOT = Path(__file__).resolve().parent
APP_FILE = PROJECT_ROOT / "streamlit_app.py"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"


def resolve_gemini_api_key() -> str:
    env_key = os.getenv("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key

    account = os.getenv("USER", "").strip()
    if not account:
        return ""

    result = subprocess.run(
        [
            "security",
            "find-generic-password",
            "-a",
            account,
            "-s",
            "GEMINI_API_KEY",
            "-w",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def pids_on_port(port: int) -> list[int]:
    result = subprocess.run(
        ["lsof", "-ti", f"tcp:{port}"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0 or not result.stdout.strip():
        return []

    pids = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    return sorted(set(pids))


def kill_pid(pid: int, sig: int) -> None:
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        pass


def clear_port(port: int) -> None:
    existing = pids_on_port(port)
    if not existing:
        return

    print(f"Port {port} is busy. Stopping process(es): {existing}")

    for pid in existing:
        kill_pid(pid, signal.SIGTERM)

    time.sleep(1.0)

    still_running = pids_on_port(port)
    if still_running:
        print(f"Force killing remaining process(es): {still_running}")
        for pid in still_running:
            kill_pid(pid, signal.SIGKILL)

    time.sleep(0.5)


def main() -> None:
    if not APP_FILE.exists():
        raise SystemExit(f"App file not found: {APP_FILE}")

    clear_port(PORT)

    python_cmd = sys.executable
    current_has_streamlit = subprocess.run(
        [sys.executable, "-c", "import streamlit"],
        capture_output=True,
        text=True,
        check=False,
    ).returncode == 0

    if not current_has_streamlit and VENV_PYTHON.exists():
        print("Current Python has no streamlit. Falling back to project venv Python.")
        python_cmd = str(VENV_PYTHON)

    command = [
        python_cmd,
        "-m",
        "streamlit",
        "run",
        str(APP_FILE),
        "--server.port",
        str(PORT),
    ]

    env = os.environ.copy()
    gemini_key = resolve_gemini_api_key()
    if gemini_key:
        env["GEMINI_API_KEY"] = gemini_key
        print("Gemini API key detected and injected for this run.")
    else:
        print("Gemini API key not found in env or macOS Keychain; AI directives will use fallback defaults.")

    print("Starting Streamlit:")
    print(" ".join(command))

    os.execvpe(command[0], command, env)


if __name__ == "__main__":
    main()
