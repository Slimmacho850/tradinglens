"""
DR Lens / Trading Lens - Cloud Deployment Entry Point
This file allows 1-click automatic deployment on Streamlit Community Cloud,
Hugging Face Spaces, Render, and other cloud providers.
"""
import sys
from pathlib import Path

# Ensure src directory is available in Python path
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Execute the dashboard
import dashboard
