"""Tests de integración de las 3 tools del agente contra Supabase (sin LLM).

Cada tool se prueba en estado limpio (no reporta desviaciones) y en estado
roto (detecta exactamente el error que inject_errors.py le inyectó).
Fixtures compartidos (estado_limpio, estado_roto) en conftest.py.
"""

import pytest

import app.agent.tools as tools
from app.agent.tools import check_metric_consistency, compare_cross_reports, detect_stale_data

from inject_errors import (
    CROSS_FACTOR,
    CROSS_PEER,
    CROSS_TARGET,
    MISMATCH_FACTOR,
    MISMATCH_TARGET,
    STALE_HOURS,
    STALE_TARGET,
)


@pytest.fixture(autouse=True)
def source_compartido(source, monkeypatch):
    """Las tools usan el mismo SourceClient de la sesión de tests."""
    monkeypatch.setattr(tools, "_source", source)


def _entrada(filas: list[dict], reporte: str, metrica: str) -> dict:
    return next(f for f in filas if f["reporte"] == reporte and f["metrica"] == metrica)


# ------------------------------------------------------------- estado limpio


def test_detect_stale_data_limpio(estado_limpio) -> None:
    resultado = detect_stale_data()
    assert resultado["umbral_warning_horas"] > 0
    assert len(resultado["snapshots"]) == 8
    assert all(s["horas_desde_actualizacion"] < 1 for s in resultado["snapshots"])


def test_check_metric_consistency_limpio(estado_limpio) -> None:
    resultado = check_metric_consistency()
    assert len(resultado["comparaciones"]) == 8
    for comp in resultado["comparaciones"]:
        assert comp["valor_fuente"] is not None
        assert comp["diferencia_pct"] == pytest.approx(0, abs=0.01)


def test_compare_cross_reports_limpio(estado_limpio) -> None:
    resultado = compare_cross_reports()
    compartidas = {c["metrica"]: c for c in resultado["metricas_compartidas"]}
    assert set(compartidas) == {"ventas_totales_mes", "margen_mes"}
    for entrada in compartidas.values():
        assert len(entrada["valores_por_reporte"]) == 2
        assert entrada["diferencia_maxima_pct"] == pytest.approx(0, abs=0.01)


# --------------------------------------------------------------- estado roto


def test_detect_stale_data_roto(estado_roto) -> None:
    resultado = detect_stale_data()
    snapshots = resultado["snapshots"]

    stale = _entrada(snapshots, *STALE_TARGET)
    assert STALE_HOURS - 1 <= stale["horas_desde_actualizacion"] <= STALE_HOURS + 1
    # Viene primero: la lista está ordenada de más vieja a más fresca
    assert snapshots[0] is stale
    # El resto sigue fresco
    assert all(s["horas_desde_actualizacion"] < 1 for s in snapshots[1:])


def test_check_metric_consistency_roto(estado_roto) -> None:
    resultado = check_metric_consistency()
    comparaciones = resultado["comparaciones"]

    mismatch = _entrada(comparaciones, *MISMATCH_TARGET)
    esperado_pct = (MISMATCH_FACTOR - 1) * 100
    assert mismatch["diferencia_pct"] == pytest.approx(esperado_pct, abs=0.2)

    # Efecto secundario esperado: el snapshot del cross-conflict también
    # difiere de la fuente (ver docstring de inject_errors.py)
    desviados = {
        (c["reporte"], c["metrica"])
        for c in comparaciones
        if abs(c["diferencia_pct"]) > 1
    }
    assert desviados == {MISMATCH_TARGET, CROSS_TARGET}


def test_compare_cross_reports_roto(estado_roto) -> None:
    resultado = compare_cross_reports()
    compartidas = {c["metrica"]: c for c in resultado["metricas_compartidas"]}

    conflicto = compartidas[CROSS_TARGET[1]]
    # diferencia máxima = (max - min) / min; el inject puso CROSS_TARGET
    # en CROSS_FACTOR (0.92) del valor de CROSS_PEER
    esperado_pct = (1 / CROSS_FACTOR - 1) * 100
    assert conflicto["diferencia_maxima_pct"] == pytest.approx(esperado_pct, abs=0.2)
    assert conflicto["valores_por_reporte"][CROSS_TARGET[0]] == pytest.approx(
        conflicto["valores_por_reporte"][CROSS_PEER[0]] * CROSS_FACTOR, rel=1e-3
    )

    # La otra métrica compartida sigue consistente
    assert compartidas["margen_mes"]["diferencia_maxima_pct"] == pytest.approx(0, abs=0.01)
