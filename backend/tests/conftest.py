"""Configura sys.path para que los tests importen `app` y los scripts de backend/scripts."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
for ruta in (BACKEND_DIR, BACKEND_DIR / "scripts"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))
