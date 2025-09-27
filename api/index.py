import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# importa a instância FastAPI
from backend.app import app  # Vercel procura por 'app'
