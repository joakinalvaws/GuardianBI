"""Rompe datos a propósito para probar las tools del agente.

Cada error mapea 1:1 con una tool del agente y se aplica sobre una métrica
DISTINTA para poder verificar cada detección por separado:

  stale_data            → ("Márgenes por Sede", "margen_lima"): timestamp -50h
  metric_mismatch       → ("Ventas Mensuales", "unidades_mes"): valor +12% vs fuente
  cross_report_conflict → ("Resumen Ejecutivo", "ventas_totales_mes"): valor -8%
                          (queda en conflicto con "Ventas Mensuales"; como efecto
                          secundario también difiere de la fuente — esperado)

Uso:
    python scripts/inject_errors.py --error stale_data
    python scripts/inject_errors.py --error metric_mismatch
    python scripts/inject_errors.py --error cross_report_conflict
    python scripts/inject_errors.py --all
    python scripts/inject_errors.py --reset   # recalcula snapshots (estado limpio)
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from supabase import Client

from seed_data import get_client, rebuild_snapshots

STALE_TARGET = ("Márgenes por Sede", "margen_lima")
STALE_HOURS = 50  # > 48h → debe clasificarse critical

MISMATCH_TARGET = ("Ventas Mensuales", "unidades_mes")
MISMATCH_FACTOR = 1.12  # +12% → diferencia > 5% → critical

CROSS_TARGET = ("Resumen Ejecutivo", "ventas_totales_mes")
CROSS_PEER = ("Ventas Mensuales", "ventas_totales_mes")
CROSS_FACTOR = 0.92  # -8% respecto al otro reporte


def _get_snapshot(client: Client, reporte: str, metrica: str) -> dict:
    """Devuelve la fila de snapshot (falla claro si el seed no corrió)."""
    rows = (
        client.table("dashboard_snapshots")
        .select("*")
        .eq("reporte", reporte)
        .eq("metrica", metrica)
        .execute()
        .data
    )
    if not rows:
        print(f"✗ No existe snapshot ({reporte}, {metrica}). ¿Corriste seed_data.py?")
        sys.exit(1)
    return rows[0]


def _update_snapshot(client: Client, snapshot_id: int, cambios: dict) -> None:
    client.table("dashboard_snapshots").update(cambios).eq("id", snapshot_id).execute()


def inject_stale_data(client: Client) -> None:
    """Envejece el timestamp de un snapshot más allá del umbral crítico."""
    reporte, metrica = STALE_TARGET
    snap = _get_snapshot(client, reporte, metrica)
    viejo = (datetime.now(timezone.utc) - timedelta(hours=STALE_HOURS)).isoformat()
    _update_snapshot(client, snap["id"], {"ultima_actualizacion": viejo})
    print(f"✓ stale_data: ({reporte}, {metrica}) ahora tiene {STALE_HOURS}h de antigüedad")


def inject_metric_mismatch(client: Client) -> None:
    """Desvía el valor de un snapshot respecto a la fuente de verdad."""
    reporte, metrica = MISMATCH_TARGET
    snap = _get_snapshot(client, reporte, metrica)
    nuevo = round(float(snap["valor"]) * MISMATCH_FACTOR, 2)
    _update_snapshot(client, snap["id"], {"valor": nuevo})
    print(
        f"✓ metric_mismatch: ({reporte}, {metrica}) "
        f"{float(snap['valor']):,.2f} → {nuevo:,.2f} (+{(MISMATCH_FACTOR - 1) * 100:.0f}%)"
    )


def inject_cross_report_conflict(client: Client) -> None:
    """Hace que la misma métrica difiera entre dos reportes."""
    reporte, metrica = CROSS_TARGET
    snap = _get_snapshot(client, reporte, metrica)
    peer = _get_snapshot(client, *CROSS_PEER)
    nuevo = round(float(peer["valor"]) * CROSS_FACTOR, 2)
    _update_snapshot(client, snap["id"], {"valor": nuevo})
    print(
        f"✓ cross_report_conflict: '{metrica}' vale {nuevo:,.2f} en {reporte} "
        f"pero {float(peer['valor']):,.2f} en {CROSS_PEER[0]} ({(1 - CROSS_FACTOR) * 100:.0f}% menos)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--error",
        choices=["stale_data", "metric_mismatch", "cross_report_conflict"],
        help="Inyecta un tipo de error específico",
    )
    group.add_argument("--all", action="store_true", help="Inyecta los 3 errores")
    group.add_argument("--reset", action="store_true", help="Recalcula snapshots desde ventas (estado limpio)")
    args = parser.parse_args()

    client = get_client()
    inyectores = {
        "stale_data": inject_stale_data,
        "metric_mismatch": inject_metric_mismatch,
        "cross_report_conflict": inject_cross_report_conflict,
    }

    if args.reset:
        rebuild_snapshots(client)
        print("\n✓ RESET COMPLETO — dashboard_snapshots coincide con ventas")
    elif args.all:
        for inyector in inyectores.values():
            inyector(client)
        print("\n✓ 3 ERRORES INYECTADOS — listos para que el agente los detecte")
    else:
        inyectores[args.error](client)
        print("\n✓ ERROR INYECTADO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
