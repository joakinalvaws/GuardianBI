"""Tests del informe: builder (HTML) y pdf (WeasyPrint). No tocan la DB."""

from datetime import datetime, timezone

from app.reports.builder import build_html
from app.reports.pdf import html_to_pdf

GENERADO_EN = datetime(2026, 6, 12, 14, 30, tzinfo=timezone.utc)


def test_html_incluye_hallazgos_formateados(resultado_critico) -> None:
    html = build_html(resultado_critico, generado_en=GENERADO_EN)

    assert "12/06/2026 14:30 UTC" in html
    assert "Atención crítica" in html
    assert resultado_critico.resumen in html
    # conteos: 2 hallazgos, 1 crítico, 1 advertencia
    assert "2 hallazgos" in html
    assert "1 crítico" in html
    assert "1 advertencia" in html
    # hallazgo crítico (stale_data, sin valores numéricos)
    assert "Datos desactualizados" in html
    assert "margen_lima" in html
    assert "—" in html
    # hallazgo warning (metric_mismatch, con valores)
    assert "Métrica inconsistente" in html
    assert "1,120.00" in html
    assert "1,000.00" in html
    assert "+12.0%" in html
    assert "Forzar un refresh completo" in html


def test_html_sin_hallazgos_muestra_estado_ok(resultado_limpio) -> None:
    html = build_html(resultado_limpio, generado_en=GENERADO_EN)

    assert "Todo en orden" in html
    assert "0 hallazgos" in html
    assert "La auditoría no encontró problemas" in html


def test_html_escapa_contenido_del_agente(resultado_limpio) -> None:
    resultado_limpio.resumen = "Comparación <script>alert(1)</script> de métricas"
    html = build_html(resultado_limpio, generado_en=GENERADO_EN)

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_pdf_renderiza_bytes_validos(resultado_critico) -> None:
    pdf = html_to_pdf(build_html(resultado_critico, generado_en=GENERADO_EN))

    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 1000
