"""Fixtures compartidos de los tests de integración contra Supabase.

También configura sys.path para que los tests importen `app` y los
scripts de backend/scripts (seed_data, inject_errors).
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
for ruta in (BACKEND_DIR, BACKEND_DIR / "scripts"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

import pytest  # noqa: E402

from app.scanner.source_client import SourceClient  # noqa: E402

from inject_errors import (  # noqa: E402
    inject_cross_report_conflict,
    inject_metric_mismatch,
    inject_stale_data,
)
from seed_data import get_client, rebuild_snapshots  # noqa: E402


@pytest.fixture(scope="session")
def client():
    return get_client()


@pytest.fixture(scope="session")
def source(client) -> SourceClient:
    return SourceClient(client)


@pytest.fixture
def estado_limpio(client) -> None:
    """Snapshots recalculados desde ventas: dashboard == fuente."""
    rebuild_snapshots(client)


@pytest.fixture
def estado_roto(client):
    """Inyecta los 3 errores y restaura el estado limpio al salir."""
    rebuild_snapshots(client)
    inject_stale_data(client)
    inject_metric_mismatch(client)
    inject_cross_report_conflict(client)
    yield
    rebuild_snapshots(client)
