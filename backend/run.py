"""Convenience launcher for the FastAPI backend on Windows/macOS/Linux.

Usage:
    python run.py
"""
import socket
import subprocess
import sys

import uvicorn


def _free_port_on_windows(port: int) -> None:
    if sys.platform != "win32":
        return
    try:
        out = subprocess.check_output(
            ["netstat", "-ano", "-p", "tcp"],
            text=True,
            errors="ignore",
        )
    except Exception:
        return

    pids: set[int] = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0].upper() == "TCP" and parts[3].upper() == "LISTENING":
            if parts[1].endswith(f":{port}"):
                try:
                    pids.add(int(parts[4]))
                except ValueError:
                    pass

    for pid in pids:
        if pid > 0:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F", "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )


def _can_bind(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8000
    if not _can_bind(host, port):
        _free_port_on_windows(port)
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=["app"],
    )
