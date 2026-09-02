import sys
from pathlib import Path

# Add src directory to system path
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dashboard import main

if __name__ == "__main__":
    main()
