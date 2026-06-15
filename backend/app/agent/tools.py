"""Las 3 herramientas de diagnóstico del agente auditor.

Cada tool consulta Supabase (o Power BI si USE_REAL_POWERBI=true) en vivo al
momento de la llamada y devuelve datos crudos (valores, diferencias, antigüedad);
la clasificación de severidad la hace el agente según las reglas de su system prompt.

Mapa tool → error inyectable (inject_errors.py):
    detect_stale_data        → stale_data
    check_metric_consistency → metric_mismatch
    compare_cross_reports    → cross_report_conflict
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone

from app.config import settings
from app.scanner.source_client import SourceClient

logger = logging.getLogger(__name__)

# Umbrales critical (los warning vienen de settings). Van incluidos en la
# salida de cada tool: junto a los datos, el modelo clasifica sin errores
# de comparación; solo en el prompt, gpt-5.4-mini a veces se equivoca.
STALE_CRITICAL_HORAS = 48
TOLERANCIA_CRITICAL_PCT = 5.0

DAX_QUERIES: dict[str, str] = {
    "ventas_totales_mes": 'EVALUATE ROW("valor", [ventas_totales_mes])',
    "unidades_mes": 'EVALUATE ROW("valor", [unidades_mes])',
    "margen_mes": 'EVALUATE ROW("valor", [margen_mes])',
}

_source: SourceClient | None = None


def _get_source() -> SourceClient:
    """SourceClient compartido entre llamadas (se crea perezosamente)."""
    global _source
    if _source is None:
        _source = SourceClient()
    return _source


def _snapshots_supabase(source: SourceClient) -> list[dict]:
    """Filas de dashboard_snapshots ordenadas por reporte y métrica."""
    return (
        source.client.table("dashboard_snapshots")
        .select("reporte,metrica,valor,ultima_actualizacion")
        .order("reporte")
        .order("metrica")
        .execute()
        .data
    )


def _snapshots_powerbi() -> list[dict]:
    """Valores actuales del dataset Power BI via DAX, en el mismo formato que Supabase."""
    from app.scanner.powerbi_client import PowerBIClient

    client = PowerBIClient()
    dataset_id = settings.powerbi_dataset_id
    last_refresh = client.get_last_refresh(dataset_id)
    ultima_actualizacion = last_refresh.isoformat() if last_refresh else datetime.now(timezone.utc).isoformat()
    filas = []
    for metrica, consulta in DAX_QUERIES.items():
        rows = client.execute_dax(dataset_id, consulta)
        valor = float(rows[0]["[valor]"])
        filas.append(
            {
                "reporte": "Power BI",
                "metrica": metrica,
                "valor": valor,
                "ultima_actualizacion": ultima_actualizacion,
            }
        )
    return filas


def _get_dashboard_rows() -> list[dict]:
    """Filas del dashboard activo (Power BI real o Supabase simulado)."""
    if settings.use_real_powerbi:
        try:
            return _snapshots_powerbi()
        except Exception as exc:
            logger.warning("PowerBI no disponible (%s); usando dashboard_snapshots.", exc)
    return _snapshots_supabase(_get_source())


def _diferencia_pct(valor: float, referencia: float) -> float | None:
    """Desviación porcentual de `valor` respecto a `referencia` (None si no aplica)."""
    if referencia == 0:
        return None
    return round((valor - referencia) / referencia * 100, 4)


def detect_stale_data() -> dict:
    """Revisa la antigüedad de cada snapshot de dashboard.

    Devuelve, por cada (reporte, metrica), las horas transcurridas desde su
    última actualización, ordenadas de más vieja a más fresca, junto con el
    umbral de frescura configurado.
    """
    ahora = datetime.now(timezone.utc)
    entradas = [
        {
            "reporte": fila["reporte"],
            "metrica": fila["metrica"],
            "ultima_actualizacion": fila["ultima_actualizacion"],
            "horas_desde_actualizacion": round(
                (ahora - datetime.fromisoformat(fila["ultima_actualizacion"])).total_seconds()
                / 3600,
                2,
            ),
        }
        for fila in _get_dashboard_rows()
    ]
    entradas.sort(key=lambda e: e["horas_desde_actualizacion"], reverse=True)
    return {
        "umbral_warning_horas": settings.stale_data_threshold_hours,
        "umbral_critical_horas": STALE_CRITICAL_HORAS,
        "snapshots": entradas,
    }


def check_metric_consistency() -> dict:
    """Compara el valor que muestra cada snapshot contra la fuente de verdad.

    Recalcula las métricas del mes desde la tabla ventas y devuelve, por cada
    (reporte, metrica), el valor del dashboard, el valor real y la diferencia
    porcentual, junto con la tolerancia configurada.
    """
    fuente = _get_source().metricas_mes_actual()
    comparaciones = []
    for fila in _get_dashboard_rows():
        valor_dashboard = float(fila["valor"])
        valor_fuente = fuente.get(fila["metrica"])
        comparaciones.append(
            {
                "reporte": fila["reporte"],
                "metrica": fila["metrica"],
                "valor_dashboard": valor_dashboard,
                "valor_fuente": valor_fuente,
                "diferencia_pct": (
                    _diferencia_pct(valor_dashboard, valor_fuente)
                    if valor_fuente is not None
                    else None
                ),
            }
        )
    return {
        "tolerancia_warning_pct": settings.metric_tolerance_pct,
        "tolerancia_critical_pct": TOLERANCIA_CRITICAL_PCT,
        "comparaciones": comparaciones,
    }


def compare_cross_reports() -> dict:
    """Busca métricas presentes en más de un reporte y compara sus valores.

    Devuelve, por cada métrica compartida, el valor que muestra cada reporte
    y la diferencia porcentual máxima entre ellos (0 si todos coinciden).
    En modo Power BI la lista siempre está vacía (hay un solo reporte).
    """
    por_metrica: dict[str, dict[str, float]] = defaultdict(dict)
    for fila in _get_dashboard_rows():
        por_metrica[fila["metrica"]][fila["reporte"]] = float(fila["valor"])

    compartidas = []
    for metrica, reportes in sorted(por_metrica.items()):
        if len(reportes) < 2:
            continue
        valores = list(reportes.values())
        maximo, minimo = max(valores), min(valores)
        compartidas.append(
            {
                "metrica": metrica,
                "valores_por_reporte": reportes,
                "diferencia_maxima_pct": _diferencia_pct(maximo, minimo) or 0.0,
            }
        )
    return {
        "tolerancia_warning_pct": settings.metric_tolerance_pct,
        "tolerancia_critical_pct": TOLERANCIA_CRITICAL_PCT,
        "metricas_compartidas": compartidas,
    }
