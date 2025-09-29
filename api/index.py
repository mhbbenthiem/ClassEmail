# api/index.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # raiz do repo
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import app  # precisa existir a variável "app"
