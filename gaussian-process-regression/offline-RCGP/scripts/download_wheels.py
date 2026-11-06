"""Download the Windows x64 / CPython 3.10 wheel set listed in requirements/freeze-py310.txt.

Run on any machine with network access and pip >= 23 (the host OS does not matter):
    python scripts/download_wheels.py

Wheels go to offline-RCGP/wheels/. pip checks every file against the SHA-256 in the
lock file. Existing wheels are kept, so the script can also fill in a wheel that is
shipped only as a `.url` placeholder (tensorflow-intel).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements" / "freeze-py310.txt"
DEST = ROOT / "wheels"


def main() -> int:
    DEST.mkdir(exist_ok=True)
    cmd = [
        sys.executable, "-m", "pip", "download",
        "--dest", str(DEST),
        "--only-binary=:all:",
        "--platform", "win_amd64",
        "--python-version", "3.10",
        "--implementation", "cp",
        "--no-deps",
        "--require-hashes",
        "-r", str(LOCK),
    ]
    print(" ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
