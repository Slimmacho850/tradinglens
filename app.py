"""
DR Lens / Trading Lens - Cloud Deployment Entry Point
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
POSSIBLE_SRCS = [
    ROOT_DIR / "src",
    ROOT_DIR / "trading lens" / "trading lens" / "src",
    ROOT_DIR / "trading lens" / "src",
]

for src in POSSIBLE_SRCS:
    if src.exists():
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
        break

from dashboard import main

if __name__ == "__main__":
    main()
