"""Tests de integración del scanner (Fase 2) contra Supabase con el seed conocido.

Verifican que SourceClient calcula las métricas correctas y que
build_audit_package refleja fielmente el estado limpio y el estado roto
(errores de inject_errors.py). Requieren haber corrido seed_data.py.

Los fixtures dejan la base en estado limpio al terminar.
"""

import pytest

from app.scanner.snapshot import build_audit_package
from app.scanner.source_client import SourceClient

from inject_errors import (
    CROSS_FACTOR,
    CROSS_PEER,
    CROSS_TARGET,
    MISMATCH_FACTOR,
    MISMATCH_TARGET,
    STALE_HOURS,
    STALE_TARGET,
    inject_cross_report_conflict,
    inject_metric_mismatch,
    inject_stale_data,
)
from seed_data import get_client, rebuild_snapshots

METRICAS_ESPERADAS = {
    "ventas_totales_mes",
    "unidades_mes",
    "margen_mes",
    "margen_lima",
    "margen_bogota",
    "margen_cdmx",
}


@pytest.fixture(scope="module")
def client():
    return get_client()


@pytest.fixture(scope="module")
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


def _snap(paquete: dict, reporte: str, metrica: str) -> dict:
    """Busca la entrada de un snapshot específico dentro del paquete."""
    return next(
        s for s in paquete["snapshots"] if s["reporte"] == reporte and s["metrica"] == metrica
    )


# ---------------------------------------------------------------- SourceClient


def test_metricas_mes_actual_estructura(source: SourceClient) -> None:
    metricas = source.metricas_mes_actual()
    assert set(metricas) == METRICAS_ESPERADAS
    assert all(valor > 0 for valor in metricas.values())
    # El margen total es la suma de los márgenes por sede
    suma_sedes = metricas["margen_lima"] + metricas["margen_bogota"] + metricas["margen_cdmx"]
    assert metricas["margen_mes"] == pytest.approx(suma_sedes, abs=0.05)
    # El margen nunca supera las ventas (los costos son positivos)
    assert metricas["margen_mes"] < metricas["ventas_totales_mes"]


def test_metricas_coinciden_con_snapshots_limpios(estado_limpio, source: SourceClient) -> None:
    metricas = source.metricas_mes_actual()
    filas = source.client.table("dashboard_snapshots").select("metrica,valor").execute().data
    assert len(filas) == 8
    for fila in filas:
        assert float(fila["valor"]) == pytest.approx(metricas[fila["metrica"]], rel=1e-9)


def test_ventas_por_producto_cuadra_con_totales(source: SourceClient) -> None:
    metricas = source.metricas_mes_actual()
    por_producto = source.ventas_por_producto_mes()
    assert 0 < len(por_producto) <= 15
    # Ordenado por monto descendente
    montos = [p["monto_total"] for p in por_producto]
    assert montos == sorted(montos, reverse=True)
    # Las sumas por producto cuadran con los totales del mes
    assert sum(montos) == pytest.approx(metricas["ventas_totales_mes"], abs=0.05)
    assert sum(p["unidades"] for p in por_producto) == metricas["unidades_mes"]


# ------------------------------------------------------------ build_audit_package


def test_paquete_estado_limpio(estado_limpio, source: SourceClient) -> None:
    paquete = build_audit_package(source)

    assert set(paquete) == {
        "generado_en", "umbrales", "fuente", "snapshots", "metricas_compartidas",
    }
    assert paquete["umbrales"]["stale_threshold_horas"] > 0
    assert set(paquete["fuente"]) == METRICAS_ESPERADAS
    assert len(paquete["snapshots"]) == 8

    for snap in paquete["snapshots"]:
        # Limpio: dashboard coincide con la fuente y los datos son frescos
        assert snap["diferencia_pct"] == pytest.approx(0, abs=0.01)
        assert snap["horas_desde_actualizacion"] < 1

    compartidas = paquete["metricas_compartidas"]
    assert set(compartidas) == {"ventas_totales_mes", "margen_mes"}
    assert set(compartidas["ventas_totales_mes"]) == {"Ventas Mensuales", "Resumen Ejecutivo"}
    assert set(compartidas["margen_mes"]) == {"Márgenes por Sede", "Resumen Ejecutivo"}
    for reportes in compartidas.values():
        valores = list(reportes.values())
        assert valores[0] == pytest.approx(valores[1], rel=1e-9)


def test_paquete_estado_roto(estado_roto, source: SourceClient) -> None:
    paquete = build_audit_package(source)

    # stale_data: el snapshot envejecido supera el umbral crítico (48h)
    stale = _snap(paquete, *STALE_TARGET)
    assert STALE_HOURS - 1 <= stale["horas_desde_actualizacion"] <= STALE_HOURS + 1

    # metric_mismatch: el dashboard se desvía el factor inyectado vs la fuente
    mismatch = _snap(paquete, *MISMATCH_TARGET)
    esperado_pct = (MISMATCH_FACTOR - 1) * 100
    assert mismatch["diferencia_pct"] == pytest.approx(esperado_pct, abs=0.2)

    # cross_report_conflict: la métrica compartida difiere entre reportes
    metrica_cross = CROSS_TARGET[1]
    compartidas = paquete["metricas_compartidas"][metrica_cross]
    assert compartidas[CROSS_TARGET[0]] == pytest.approx(
        compartidas[CROSS_PEER[0]] * CROSS_FACTOR, rel=1e-3
    )

    # Las métricas no tocadas siguen limpias
    intactos = _snap(paquete, "Márgenes por Sede", "margen_bogota")
    assert intactos["diferencia_pct"] == pytest.approx(0, abs=0.01)
    assert intactos["horas_desde_actualizacion"] < 1
