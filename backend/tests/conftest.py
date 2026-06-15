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

from app.agent.models import AuditResult, Finding  # noqa: E402
from app.config import settings  # noqa: E402
from app.scanner.source_client import SourceClient  # noqa: E402

from inject_errors import (  # noqa: E402
    inject_cross_report_conflict,
    inject_metric_mismatch,
    inject_stale_data,
)
from seed_data import get_client, rebuild_snapshots  # noqa: E402


@pytest.fixture(autouse=True)
def forzar_modo_supabase(monkeypatch) -> None:
    """Los tests de integración siempre usan dashboard_snapshots, no Power BI real."""
    monkeypatch.setattr(settings, "use_real_powerbi", False)


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
def resultado_critico() -> AuditResult:
    """AuditResult de ejemplo con un crítico y una advertencia (sin LLM)."""
    return AuditResult(
        estado_general="critical",
        resumen="El margen de Lima lleva 50 horas sin actualizarse y las unidades del mes difieren 12%.",
        findings=[
            Finding(
                severidad="critical",
                tipo="stale_data",
                metrica="margen_lima",
                reporte="Márgenes por Sede",
                valor_dashboard=None,
                valor_fuente=None,
                diferencia_pct=None,
                causa_probable="El refresh del dataset falló hace dos días.",
                recomendacion="Revisar el refresh programado en Power BI.",
            ),
            Finding(
                severidad="warning",
                tipo="metric_mismatch",
                metrica="unidades_mes",
                reporte="Ventas Mensuales",
                valor_dashboard=1120.0,
                valor_fuente=1000.0,
                diferencia_pct=12.0,
                causa_probable="El dashboard quedó con un valor inflado tras una carga parcial.",
                recomendacion="Forzar un refresh completo del reporte Ventas Mensuales.",
            ),
        ],
    )


@pytest.fixture
def resultado_limpio() -> AuditResult:
    """AuditResult sin hallazgos (estado ok)."""
    return AuditResult(
        estado_general="ok",
        resumen="Todos los dashboards coinciden con la fuente y están actualizados.",
        findings=[],
    )


@pytest.fixture
def estado_roto(client):
    """Inyecta los 3 errores y restaura el estado limpio al salir."""
    rebuild_snapshots(client)
    inject_stale_data(client)
    inject_metric_mismatch(client)
    inject_cross_report_conflict(client)
    yield
    rebuild_snapshots(client)
