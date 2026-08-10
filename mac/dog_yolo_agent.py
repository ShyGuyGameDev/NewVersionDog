#!/usr/bin/env python3
"""
LaunchAgent entrypoint for Mac YOLO.

Keeps dog_yolo_mac.py running headlessly so the robot website can:
  - hit /start when the camera turns on
  - pull /annotated.jpg for the right-hand camera panel

If the YOLO process exits, it is restarted after a short delay.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
# NewVersionDog/mac → workspace root (where .venv lives)
ROOT = HERE.parent.parent
YOLO_SCRIPT = HERE / "dog_yolo_mac.py"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
DEFAULT_CAMERA_URL = os.environ.get("DOG_CAMERA_URL", "http://10.1.1.146:8000/frame.jpg")
SERVE_PORT = os.environ.get("DOG_YOLO_PORT", "8010")


def python_bin() -> str:
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def main():
    if not YOLO_SCRIPT.exists():
        logger.error("Missing %s", YOLO_SCRIPT)
        sys.exit(1)

    py = python_bin()
    cmd = [
        py,
        str(YOLO_SCRIPT),
        "--url", DEFAULT_CAMERA_URL,
        "--serve-port", str(SERVE_PORT),
        "--no-window",
    ]
    logger.info("Agent supervising: %s", " ".join(cmd))

    while True:
        proc = subprocess.Popen(cmd, cwd=str(HERE))
        code = proc.wait()
        logger.warning("dog_yolo_mac.py exited with code %s; restarting in 3s", code)
        time.sleep(3)


if __name__ == "__main__":
    main()
