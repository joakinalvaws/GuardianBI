"""Flujo end-to-end del scheduler con todas las dependencias mockeadas.

Verifica la orquestación (orden, persistencia, política de notificación);
el ciclo real se valida manualmente con `python -m app.scheduler --run-now`.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scheduler import ejecutar_auditoria, formatear_resumen

AUDIT_ID = "11111111-2222-3333-4444-555555555555"
PDF_URL = "https://example.supabase.co/storage/v1/object/public/informes/x.pdf"


def _mocks_del_ciclo(resultado):
    """Patches comunes: repo, scanner, agente, render de PDF y telegram."""
    repo = MagicMock()
    repo.crear_auditoria.return_value = AUDIT_ID
    repo.subir_pdf.return_value = PDF_URL
    return {
        "repo": patch("app.scheduler.AuditRepository", return_value=repo),
        "scanner": patch("app.scheduler.build_audit_package", return_value={"snapshots": []}),
        "agente": patch("app.scheduler.run_audit", AsyncMock(return_value=resultado)),
        "html": patch("app.scheduler.build_html", return_value="<html></html>"),
        "pdf": patch("app.scheduler.html_to_pdf", return_value=b"%PDF-1.7 informe"),
        "send_report": patch("app.scheduler.telegram.send_report"),
        "send_summary": patch("app.scheduler.telegram.send_summary"),
    }, repo


@pytest.mark.asyncio
async def test_con_hallazgos_persiste_y_envia_pdf(resultado_critico) -> None:
    patches, repo = _mocks_del_ciclo(resultado_critico)
    with (
        patches["repo"], patches["scanner"], patches["agente"],
        patches["html"], patches["pdf"],
        patches["send_report"] as send_report, patches["send_summary"] as send_summary,
    ):
        resultado = await ejecutar_auditoria()

    assert resultado is resultado_critico
    repo.guardar_resultado.assert_called_once_with(AUDIT_ID, resultado_critico)
    repo.subir_pdf.assert_called_once_with(AUDIT_ID, b"%PDF-1.7 informe")
    repo.marcar_fallida.assert_not_called()

    send_summary.assert_not_called()
    send_report.assert_called_once()
    mensaje, ruta_pdf = send_report.call_args.args
    assert PDF_URL in mensaje
    assert "1 críticos, 1 advertencias" in mensaje
    assert ruta_pdf.name == f"informe-{AUDIT_ID}.pdf"


@pytest.mark.asyncio
async def test_sin_hallazgos_solo_envia_resumen(resultado_limpio) -> None:
    patches, repo = _mocks_del_ciclo(resultado_limpio)
    with (
        patches["repo"], patches["scanner"], patches["agente"],
        patches["html"], patches["pdf"],
        patches["send_report"] as send_report, patches["send_summary"] as send_summary,
    ):
        await ejecutar_auditoria()

    # el PDF se sube igual (queda en pdf_url para la web), pero no se adjunta
    repo.subir_pdf.assert_called_once()
    send_report.assert_not_called()
    send_summary.assert_called_once()
    assert "Todo en orden" in send_summary.call_args.args[0]


@pytest.mark.asyncio
async def test_si_el_agente_falla_marca_la_auditoria_como_fallida(resultado_limpio) -> None:
    patches, repo = _mocks_del_ciclo(resultado_limpio)
    patches["agente"] = patch(
        "app.scheduler.run_audit", AsyncMock(side_effect=RuntimeError("timeout del LLM"))
    )
    with (
        patches["repo"], patches["scanner"], patches["agente"],
        patches["send_report"] as send_report, patches["send_summary"] as send_summary,
        pytest.raises(RuntimeError, match="timeout del LLM"),
    ):
        await ejecutar_auditoria()

    repo.marcar_fallida.assert_called_once_with(AUDIT_ID, "timeout del LLM")
    repo.guardar_resultado.assert_not_called()
    send_report.assert_not_called()
    send_summary.assert_not_called()


def test_formatear_resumen_estado_ok(resultado_limpio) -> None:
    mensaje = formatear_resumen(resultado_limpio, PDF_URL)

    assert mensaje.startswith("✅ Dashboard Guardian")
    assert "Todo en orden (0 críticos, 0 advertencias)" in mensaje
    assert resultado_limpio.resumen in mensaje
    assert mensaje.endswith(f"📄 Informe: {PDF_URL}")
