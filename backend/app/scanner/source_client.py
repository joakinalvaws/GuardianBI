"""Consultas de agregación sobre la fuente de verdad (tabla ventas).

Calcula las métricas del mes actual directamente desde Supabase para
contrastarlas con lo que muestran los dashboards (dashboard_snapshots).
En el MVP la fuente de verdad son las tablas de negocio; en Fase 6 estas
mismas métricas se contrastarán con la Power BI REST API (ver ADR-001).
"""

from datetime import date

from supabase import Client, create_client

from app.config import settings

PAGE_SIZE = 1000  # límite por request de PostgREST

# Clave de métrica de margen según la ciudad de la sede
MARGEN_METRICA_POR_CIUDAD = {
    "Lima": "margen_lima",
    "Bogotá": "margen_bogota",
    "Ciudad de México": "margen_cdmx",
}


def get_client() -> Client:
    """Cliente Supabase con la secret key (backend, salta RLS)."""
    return create_client(settings.supabase_url, settings.supabase_secret_key)


class SourceClient:
    """Lee y agrega la fuente de verdad para el mes en curso."""

    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_client()

    def _fetch_all(self, table: str, select: str, fecha_desde: date | None = None) -> list[dict]:
        """Trae todas las filas de una tabla paginando de a PAGE_SIZE."""
        rows: list[dict] = []
        start = 0
        while True:
            query = self.client.table(table).select(select).range(start, start + PAGE_SIZE - 1)
            if fecha_desde is not None:
                query = query.gte("fecha", fecha_desde.isoformat())
            batch = query.execute().data
            rows.extend(batch)
            if len(batch) < PAGE_SIZE:
                return rows
            start += PAGE_SIZE

    def _contexto_mes(self) -> tuple[list[dict], dict[int, dict], dict[int, dict]]:
        """Ventas del mes actual + catálogos de productos y sedes indexados por id."""
        primer_dia_mes = date.today().replace(day=1)
        productos = {
            p["id"]: p
            for p in self._fetch_all("productos", "id,nombre,categoria,costo_unitario,precio_venta")
        }
        sedes = {s["id"]: s for s in self._fetch_all("sedes", "id,nombre,ciudad")}
        ventas = self._fetch_all(
            "ventas", "sede_id,producto_id,cantidad,monto_total", fecha_desde=primer_dia_mes
        )
        return ventas, productos, sedes

    def metricas_mes_actual(self) -> dict[str, float]:
        """Métricas agregadas del mes en curso, con las mismas claves que usa
        `dashboard_snapshots.metrica`: ventas_totales_mes, unidades_mes,
        margen_mes y margen por sede (margen_lima, margen_bogota, margen_cdmx).
        """
        ventas, productos, sedes = self._contexto_mes()

        ventas_totales = 0.0
        unidades = 0
        margen_total = 0.0
        margen_por_sede: dict[int, float] = {sede_id: 0.0 for sede_id in sedes}
        for v in ventas:
            p = productos[v["producto_id"]]
            margen = v["cantidad"] * (float(p["precio_venta"]) - float(p["costo_unitario"]))
            ventas_totales += float(v["monto_total"])
            unidades += v["cantidad"]
            margen_total += margen
            margen_por_sede[v["sede_id"]] += margen

        metricas = {
            "ventas_totales_mes": round(ventas_totales, 2),
            "unidades_mes": float(unidades),
            "margen_mes": round(margen_total, 2),
        }
        for sede_id, margen in margen_por_sede.items():
            clave = MARGEN_METRICA_POR_CIUDAD[sedes[sede_id]["ciudad"]]
            metricas[clave] = round(margen, 2)
        return metricas

    def ventas_por_producto_mes(self) -> list[dict]:
        """Unidades y monto vendidos por producto en el mes, ordenado por monto desc."""
        ventas, productos, _ = self._contexto_mes()
        acumulado: dict[int, dict] = {}
        for v in ventas:
            p = productos[v["producto_id"]]
            fila = acumulado.setdefault(
                v["producto_id"],
                {"producto": p["nombre"], "categoria": p["categoria"], "unidades": 0, "monto_total": 0.0},
            )
            fila["unidades"] += v["cantidad"]
            fila["monto_total"] += float(v["monto_total"])

        filas = sorted(acumulado.values(), key=lambda f: f["monto_total"], reverse=True)
        for fila in filas:
            fila["monto_total"] = round(fila["monto_total"], 2)
        return filas
