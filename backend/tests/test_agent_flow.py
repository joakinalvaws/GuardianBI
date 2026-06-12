"""Flujo end-to-end del agente con el Runner mockeado (no consume tokens).

La detección real (agente + LLM) se verifica manualmente desde CLI:
`python -m app.agent.guardian` con datos limpios y con errores inyectados.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.agent.guardian import guardian_agent, run_audit
from app.agent.models import AuditResult, Finding
from app.config import settings


def test_configuracion_del_agente() -> None:
    assert guardian_agent.model == settings.openai_model
    assert guardian_agent.output_type is AuditResult
    nombres = {tool.name for tool in guardian_agent.tools}
    assert nombres == {"detect_stale_data", "check_metric_consistency", "compare_cross_reports"}


@pytest.mark.asyncio
async def test_run_audit_pasa_el_snapshot_y_devuelve_final_output() -> None:
    esperado = AuditResult(estado_general="ok", resumen="Todo en orden.", findings=[])
    mock_run = AsyncMock(return_value=SimpleNamespace(final_output=esperado))

    with patch("app.agent.guardian.Runner.run", mock_run):
        resultado = await run_audit({"fuente": {"ventas_totales_mes": 39845.3}})

    assert resultado is esperado
    agente, = mock_run.call_args.args
    assert agente is guardian_agent
    assert "ventas_totales_mes" in mock_run.call_args.kwargs["input"]


def test_finding_espeja_la_tabla_findings() -> None:
    finding = Finding(
        severidad="critical",
        tipo="stale_data",
        metrica="margen_lima",
        reporte="Márgenes por Sede",
        valor_dashboard=None,
        valor_fuente=None,
        diferencia_pct=None,
        causa_probable="El refresh del dataset falló hace dos días.",
        recomendacion="Revisar el refresh programado en Power BI.",
    )
    columnas_findings = {
        "severidad", "tipo", "metrica", "reporte", "valor_dashboard",
        "valor_fuente", "diferencia_pct", "causa_probable", "recomendacion",
    }
    assert set(finding.model_dump()) == columnas_findings


def test_finding_rechaza_severidad_invalida() -> None:
    with pytest.raises(ValidationError):
        Finding(
            severidad="urgente",  # no es critical | warning | ok
            tipo="stale_data",
            metrica="x",
            reporte=None,
            valor_dashboard=None,
            valor_fuente=None,
            diferencia_pct=None,
            causa_probable="",
            recomendacion="",
        )
