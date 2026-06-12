"""Genera datos de negocio coherentes para Dashboard Guardian.

Crea 3 sedes, 15 productos y ~6 meses de ventas (~5000 filas), y puebla
`dashboard_snapshots` con los valores CORRECTOS calculados desde `ventas`
(estado limpio: el dashboard coincide con la fuente de verdad).

Determinista (random.seed fijo): correrlo dos veces produce los mismos datos.

Uso:
    python scripts/seed_data.py

Requiere haber ejecutado backend/db/schema.sql en el SQL Editor de Supabase.
"""

import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from supabase import Client, create_client

from app.config import settings
from app.scanner.source_client import SourceClient

RANDOM_SEED = 42
DIAS_HISTORICO = 182  # ~6 meses
TOTAL_VENTAS = 5000
BATCH_SIZE = 500

SEDES = [
    {"nombre": "Sede Lima", "ciudad": "Lima"},
    {"nombre": "Sede Bogotá", "ciudad": "Bogotá"},
    {"nombre": "Sede CDMX", "ciudad": "Ciudad de México"},
]

PRODUCTOS = [
    {"nombre": "Café molido 250g", "categoria": "Abarrotes", "costo_unitario": 12.50, "precio_venta": 22.90},
    {"nombre": "Café en grano 1kg", "categoria": "Abarrotes", "costo_unitario": 38.00, "precio_venta": 64.90},
    {"nombre": "Arroz 5kg", "categoria": "Abarrotes", "costo_unitario": 18.50, "precio_venta": 27.90},
    {"nombre": "Aceite vegetal 1L", "categoria": "Abarrotes", "costo_unitario": 8.90, "precio_venta": 13.50},
    {"nombre": "Leche entera 1L", "categoria": "Lácteos", "costo_unitario": 3.20, "precio_venta": 4.90},
    {"nombre": "Yogurt natural 1L", "categoria": "Lácteos", "costo_unitario": 5.80, "precio_venta": 9.50},
    {"nombre": "Queso fresco 500g", "categoria": "Lácteos", "costo_unitario": 9.00, "precio_venta": 14.90},
    {"nombre": "Pan integral", "categoria": "Panadería", "costo_unitario": 4.50, "precio_venta": 8.90},
    {"nombre": "Croissant", "categoria": "Panadería", "costo_unitario": 2.10, "precio_venta": 4.50},
    {"nombre": "Torta de chocolate", "categoria": "Panadería", "costo_unitario": 18.00, "precio_venta": 35.00},
    {"nombre": "Jugo de naranja 1L", "categoria": "Bebidas", "costo_unitario": 4.00, "precio_venta": 7.90},
    {"nombre": "Agua mineral 600ml", "categoria": "Bebidas", "costo_unitario": 0.80, "precio_venta": 2.50},
    {"nombre": "Gaseosa 1.5L", "categoria": "Bebidas", "costo_unitario": 3.50, "precio_venta": 6.90},
    {"nombre": "Detergente 2kg", "categoria": "Limpieza", "costo_unitario": 11.00, "precio_venta": 18.90},
    {"nombre": "Papel toalla x2", "categoria": "Limpieza", "costo_unitario": 6.50, "precio_venta": 10.90},
]


def get_client() -> Client:
    """Cliente Supabase con la secret key (escritura, salta RLS)."""
    return create_client(settings.supabase_url, settings.supabase_secret_key)


def wipe_business_data(client: Client) -> None:
    """Borra ventas, snapshots, productos y sedes (en orden de FKs)."""
    for table in ("ventas", "dashboard_snapshots", "productos", "sedes"):
        client.table(table).delete().gte("id", 0).execute()
    print("✓ Tablas de negocio vaciadas")


def seed_sedes_y_productos(client: Client) -> tuple[list[dict], list[dict]]:
    """Inserta sedes y productos; devuelve las filas con sus ids."""
    sedes = client.table("sedes").insert(SEDES).execute().data
    productos = client.table("productos").insert(PRODUCTOS).execute().data
    print(f"✓ {len(sedes)} sedes y {len(productos)} productos insertados")
    return sedes, productos


def seed_ventas(client: Client, sedes: list[dict], productos: list[dict]) -> int:
    """Genera TOTAL_VENTAS filas en los últimos DIAS_HISTORICO días."""
    hoy = date.today()
    filas = []
    for _ in range(TOTAL_VENTAS):
        producto = random.choice(productos)
        cantidad = random.randint(1, 15)
        fecha = hoy - timedelta(days=random.randint(0, DIAS_HISTORICO))
        filas.append(
            {
                "sede_id": random.choice(sedes)["id"],
                "producto_id": producto["id"],
                "fecha": fecha.isoformat(),
                "cantidad": cantidad,
                "monto_total": round(cantidad * producto["precio_venta"], 2),
            }
        )
    for i in range(0, len(filas), BATCH_SIZE):
        client.table("ventas").insert(filas[i : i + BATCH_SIZE]).execute()
    print(f"✓ {len(filas)} ventas insertadas ({DIAS_HISTORICO} días de histórico)")
    return len(filas)


def compute_snapshot_values(client: Client) -> dict[tuple[str, str], float]:
    """Distribuye las métricas reales (SourceClient) en los reportes simulados.

    Devuelve {(reporte, metrica): valor}. Incluye a propósito métricas
    compartidas entre reportes (ventas_totales_mes y margen_mes) para que
    compare_cross_reports tenga material real que comparar en Fase 3.
    """
    m = SourceClient(client).metricas_mes_actual()
    return {
        ("Ventas Mensuales", "ventas_totales_mes"): m["ventas_totales_mes"],
        ("Ventas Mensuales", "unidades_mes"): m["unidades_mes"],
        # Métricas compartidas entre reportes (pares para cross_report):
        ("Resumen Ejecutivo", "ventas_totales_mes"): m["ventas_totales_mes"],
        ("Resumen Ejecutivo", "margen_mes"): m["margen_mes"],
        ("Márgenes por Sede", "margen_mes"): m["margen_mes"],
        ("Márgenes por Sede", "margen_lima"): m["margen_lima"],
        ("Márgenes por Sede", "margen_bogota"): m["margen_bogota"],
        ("Márgenes por Sede", "margen_cdmx"): m["margen_cdmx"],
    }


def rebuild_snapshots(client: Client) -> dict[tuple[str, str], float]:
    """Recalcula `dashboard_snapshots` desde `ventas` con timestamps frescos.

    Estado limpio: dashboard == fuente de verdad. Lo usa también
    inject_errors.py --reset.
    """
    valores = compute_snapshot_values(client)
    ahora = datetime.now(timezone.utc).isoformat()
    filas = [
        {
            "reporte": reporte,
            "metrica": metrica,
            "valor": valor,
            "ultima_actualizacion": ahora,
            "updated_at": ahora,
        }
        for (reporte, metrica), valor in valores.items()
    ]
    client.table("dashboard_snapshots").upsert(filas, on_conflict="reporte,metrica").execute()
    print(f"✓ {len(filas)} snapshots recalculados desde ventas (estado limpio)")
    return valores


def main() -> int:
    random.seed(RANDOM_SEED)
    client = get_client()

    print("→ Sembrando datos de negocio en Supabase…\n")
    wipe_business_data(client)
    sedes, productos = seed_sedes_y_productos(client)
    seed_ventas(client, sedes, productos)
    valores = rebuild_snapshots(client)

    print("\nValores de snapshots (mes actual):")
    for (reporte, metrica), valor in sorted(valores.items()):
        print(f"  {reporte:20s} | {metrica:22s} | {valor:>12,.2f}")
    print("\n✓ SEED COMPLETO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
