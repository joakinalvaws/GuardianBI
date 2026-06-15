"""Arma el paquete de estado dashboard-vs-fuente para el agente auditor.

Junta lo que los dashboards "muestran" (dashboard_snapshots o Power BI real)
con los valores reales calculados desde ventas (SourceClient) y los timestamps
de actualización. El agente (Fase 3) recibe este dict como input de auditoría.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone

from app.config import settings
from app.scanner.source_client import SourceClient

logger = logging.getLogger(__name__)

DAX_QUERIES: dict[str, str] = {
    "ventas_totales_mes": 'EVALUATE ROW("valor", [ventas_totales_mes])',
    "unidades_mes": 'EVALUATE ROW("valor", [unidades_mes])',
    "margen_mes": 'EVALUATE ROW("valor", [margen_mes])',
}


def _horas_desde(timestamp_iso: str, ahora: datetime) -> float:
    """Horas transcurridas desde un timestamp ISO de Supabase."""
    momento = datetime.fromisoformat(timestamp_iso)
    return (ahora - momento).total_seconds() / 3600


def _diferencia_pct(valor_dashboard: float, valor_fuente: float | None) -> float | None:
    """Desviación porcentual del dashboard respecto a la fuente (None si no aplica)."""
    if valor_fuente is None or valor_fuente == 0:
        return None
    return round((valor_dashboard - valor_fuente) / valor_fuente * 100, 4)


def _leer_filas_supabase(source: SourceClient) -> list[dict]:
    """Filas de dashboard_snapshots ordenadas por reporte y métrica."""
    return (
        source.client.table("dashboard_snapshots")
        .select("reporte,metrica,valor,ultima_actualizacion")
        .order("reporte")
        .order("metrica")
        .execute()
        .data
    )


def _leer_filas_powerbi() -> list[dict]:
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


def build_audit_package(source: SourceClient | None = None) -> dict:
    """Devuelve el estado completo a auditar en un solo dict.

    Cuando USE_REAL_POWERBI=true consulta el dataset Power BI via DAX;
    si falla, hace fallback a dashboard_snapshots con un aviso en el log.

    Estructura:
        generado_en           timestamp UTC de la corrida
        umbrales              configuración vigente (stale y tolerancia)
        fuente                {metrica: valor real calculado desde ventas}
        snapshots             una entrada por (reporte, metrica) del dashboard,
                              con valor, desviación vs fuente y antigüedad
        metricas_compartidas  {metrica: {reporte: valor}} solo para métricas
                              presentes en más de un reporte (cross-report)
    """
    source = source or SourceClient()
    fuente = source.metricas_mes_actual()

    if settings.use_real_powerbi:
        try:
            filas = _leer_filas_powerbi()
        except Exception as exc:
            logger.warning("PowerBI no disponible (%s); usando dashboard_snapshots.", exc)
            filas = _leer_filas_supabase(source)
    else:
        filas = _leer_filas_supabase(source)

    ahora = datetime.now(timezone.utc)
    snapshots: list[dict] = []
    por_metrica: dict[str, dict[str, float]] = defaultdict(dict)
    for fila in filas:
        valor_dashboard = float(fila["valor"])
        valor_fuente = fuente.get(fila["metrica"])
        snapshots.append(
            {
                "reporte": fila["reporte"],
                "metrica": fila["metrica"],
                "valor_dashboard": valor_dashboard,
                "valor_fuente": valor_fuente,
                "diferencia_pct": _diferencia_pct(valor_dashboard, valor_fuente),
                "ultima_actualizacion": fila["ultima_actualizacion"],
                "horas_desde_actualizacion": round(
                    _horas_desde(fila["ultima_actualizacion"], ahora), 2
                ),
            }
        )
        por_metrica[fila["metrica"]][fila["reporte"]] = valor_dashboard

    return {
        "generado_en": ahora.isoformat(),
        "umbrales": {
            "stale_threshold_horas": settings.stale_data_threshold_hours,
            "tolerancia_pct": settings.metric_tolerance_pct,
        },
        "fuente": fuente,
        "snapshots": snapshots,
        "metricas_compartidas": {
            metrica: reportes for metrica, reportes in por_metrica.items() if len(reportes) > 1
        },
    }
