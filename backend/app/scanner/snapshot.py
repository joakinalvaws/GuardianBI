"""Arma el paquete de estado dashboard-vs-fuente para el agente auditor.

Junta lo que los dashboards "muestran" (dashboard_snapshots) con los valores
reales calculados desde ventas (SourceClient) y los timestamps de
actualización. El agente (Fase 3) recibe este dict como input de auditoría.
"""

from collections import defaultdict
from datetime import datetime, timezone

from app.config import settings
from app.scanner.source_client import SourceClient


def _horas_desde(timestamp_iso: str, ahora: datetime) -> float:
    """Horas transcurridas desde un timestamp ISO de Supabase."""
    momento = datetime.fromisoformat(timestamp_iso)
    return (ahora - momento).total_seconds() / 3600


def _diferencia_pct(valor_dashboard: float, valor_fuente: float | None) -> float | None:
    """Desviación porcentual del dashboard respecto a la fuente (None si no aplica)."""
    if valor_fuente is None or valor_fuente == 0:
        return None
    return round((valor_dashboard - valor_fuente) / valor_fuente * 100, 4)


def build_audit_package(source: SourceClient | None = None) -> dict:
    """Devuelve el estado completo a auditar en un solo dict.

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
    filas = (
        source.client.table("dashboard_snapshots")
        .select("reporte,metrica,valor,ultima_actualizacion")
        .order("reporte")
        .order("metrica")
        .execute()
        .data
    )

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
