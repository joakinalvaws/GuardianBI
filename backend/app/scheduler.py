"""Ciclo de auditoría completo: scanner → agente → persistencia → informe → Telegram.

Fase 4: trigger manual desde línea de comandos (requiere venv activo):

    cd backend && python -m app.scheduler --run-now

Fase 6 conecta este mismo ciclo a un cron de GitHub Actions.
"""

import argparse
import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.agent.guardian import run_audit
from app.agent.models import AuditResult
from app.db.repository import AuditRepository
from app.delivery import telegram
from app.reports.builder import build_html, fecha_local_str
from app.reports.pdf import html_to_pdf
from app.scanner.snapshot import build_audit_package

EMOJI_POR_ESTADO = {"ok": "✅", "warning": "🟡", "critical": "🔴"}
ESTADO_LABELS = {
    "ok": "Todo en orden",
    "warning": "Con advertencias",
    "critical": "Atención crítica",
}


def formatear_resumen(resultado: AuditResult, pdf_url: str) -> str:
    """Mensaje de Telegram: estado, conteos, resumen del agente y link al PDF."""
    criticos = sum(1 for f in resultado.findings if f.severidad == "critical")
    advertencias = sum(1 for f in resultado.findings if f.severidad == "warning")
    ahora = datetime.now(timezone.utc)
    lineas = [
        f"{EMOJI_POR_ESTADO[resultado.estado_general]} Dashboard Guardian — {fecha_local_str(ahora)}",
        f"Estado: {ESTADO_LABELS[resultado.estado_general]}"
        f" ({criticos} críticos, {advertencias} advertencias)",
        "",
        resultado.resumen,
        "",
        f"📄 Informe: {pdf_url}",
    ]
    return "\n".join(lineas)


async def ejecutar_auditoria() -> AuditResult:
    """Corre una auditoría end-to-end y notifica por Telegram.

    Siempre genera y sube el PDF (queda en audits.pdf_url para la web);
    el adjunto por Telegram solo va cuando hay hallazgos — sin hallazgos
    se envía únicamente el resumen.
    """
    repo = AuditRepository()
    audit_id = repo.crear_auditoria()
    print(f"→ Auditoría {audit_id} iniciada")

    try:
        print("→ Armando paquete de estado (scanner)…")
        paquete = build_audit_package()
        print("→ Auditando con el agente…")
        resultado = await run_audit(paquete)
    except Exception as exc:
        repo.marcar_fallida(audit_id, str(exc))
        raise

    repo.guardar_resultado(audit_id, resultado)
    print(f"→ Resultado guardado: {resultado.estado_general}, {len(resultado.findings)} hallazgos")

    pdf = html_to_pdf(build_html(resultado))
    pdf_url = repo.subir_pdf(audit_id, pdf)
    print(f"→ PDF subido: {pdf_url}")

    mensaje = formatear_resumen(resultado, pdf_url)
    if resultado.findings:
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / f"informe-{audit_id}.pdf"
            ruta.write_bytes(pdf)
            telegram.send_report(mensaje, ruta)
        print("→ Telegram: resumen + PDF adjunto enviados")
    else:
        telegram.send_summary(mensaje)
        print("→ Telegram: resumen enviado (sin hallazgos, no se adjunta PDF)")

    return resultado


def main() -> int:
    parser = argparse.ArgumentParser(description="Ciclo de auditoría de Dashboard Guardian")
    parser.add_argument(
        "--run-now", action="store_true", help="ejecuta una auditoría completa ahora"
    )
    args = parser.parse_args()
    if not args.run_now:
        parser.error("por ahora solo soporta --run-now (el cron llega en Fase 6)")
    asyncio.run(ejecutar_auditoria())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
