"""Construcción del informe HTML a partir del resultado del agente.

Renderiza `templates/informe.html` con Jinja2. Todo el formateo
(etiquetas en español, números, fechas) vive aquí; la plantilla solo
pinta valores ya formateados.
"""

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.agent.models import AuditResult, Finding

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

ESTADO_LABELS = {
    "ok": "Todo en orden",
    "warning": "Con advertencias",
    "critical": "Atención crítica",
}
SEVERIDAD_LABELS = {"critical": "CRÍTICO", "warning": "ADVERTENCIA", "ok": "OK"}
TIPO_LABELS = {
    "stale_data": "Datos desactualizados",
    "metric_mismatch": "Métrica inconsistente",
    "cross_report_conflict": "Conflicto entre reportes",
}

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)


def _fmt_numero(valor: float | None) -> str:
    """Número con separador de miles y 2 decimales; em dash si es null."""
    return f"{valor:,.2f}" if valor is not None else "—"


def _fmt_pct(valor: float | None) -> str:
    return f"{valor:+.1f}%" if valor is not None else "—"


def _contexto_finding(finding: Finding) -> dict:
    """Finding formateado para la plantilla."""
    return {
        "severidad": finding.severidad,
        "severidad_label": SEVERIDAD_LABELS[finding.severidad],
        "tipo_label": TIPO_LABELS[finding.tipo],
        "metrica": finding.metrica,
        "reporte": finding.reporte,
        "valor_dashboard": _fmt_numero(finding.valor_dashboard),
        "valor_fuente": _fmt_numero(finding.valor_fuente),
        "diferencia_pct": _fmt_pct(finding.diferencia_pct),
        "causa_probable": finding.causa_probable,
        "recomendacion": finding.recomendacion,
    }


def build_html(resultado: AuditResult, generado_en: datetime | None = None) -> str:
    """Renderiza el informe completo de la auditoría como HTML."""
    generado_en = generado_en or datetime.now(timezone.utc)
    plantilla = _env.get_template("informe.html")
    return plantilla.render(
        generado_en=f"{generado_en:%d/%m/%Y %H:%M} UTC",
        estado_general=resultado.estado_general,
        estado_label=ESTADO_LABELS[resultado.estado_general],
        resumen=resultado.resumen,
        total=len(resultado.findings),
        criticos=sum(1 for f in resultado.findings if f.severidad == "critical"),
        advertencias=sum(1 for f in resultado.findings if f.severidad == "warning"),
        findings=[_contexto_finding(f) for f in resultado.findings],
    )
