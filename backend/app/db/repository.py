"""Persistencia de auditorías: tablas audits/findings y PDF en Storage.

Ciclo de vida de una auditoría (lo orquesta app/scheduler.py):
crear_auditoria() al inicio (estado running) → guardar_resultado() con el
AuditResult del agente (estado completed) → subir_pdf() con el informe.
Si el agente falla, marcar_fallida() deja el registro en estado failed.
"""

from supabase import Client

from app.agent.models import AuditResult
from app.scanner.source_client import get_client

BUCKET_INFORMES = "informes"


class AuditRepository:
    """CRUD de auditorías y hallazgos sobre Supabase."""

    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_client()

    def crear_auditoria(self) -> str:
        """Inserta una auditoría en estado running y devuelve su id (uuid)."""
        fila = self.client.table("audits").insert({"estado": "running"}).execute().data[0]
        return fila["id"]

    def guardar_resultado(self, audit_id: str, resultado: AuditResult) -> None:
        """Marca la auditoría como completed y persiste sus hallazgos.

        Finding espeja las columnas de la tabla findings, así que los
        hallazgos se insertan con model_dump() sin transformaciones.
        """
        criticos = sum(1 for f in resultado.findings if f.severidad == "critical")
        advertencias = sum(1 for f in resultado.findings if f.severidad == "warning")
        self.client.table("audits").update(
            {
                "estado": "completed",
                "total_findings": len(resultado.findings),
                "criticos": criticos,
                "advertencias": advertencias,
                "resumen": resultado.resumen,
            }
        ).eq("id", audit_id).execute()

        if resultado.findings:
            filas = [{"audit_id": audit_id, **f.model_dump()} for f in resultado.findings]
            self.client.table("findings").insert(filas).execute()

    def marcar_fallida(self, audit_id: str, error: str) -> None:
        """Marca la auditoría como failed dejando el error en el resumen."""
        self.client.table("audits").update(
            {"estado": "failed", "resumen": f"Error: {error}"}
        ).eq("id", audit_id).execute()

    def _asegurar_bucket(self) -> None:
        """Crea el bucket público de informes si todavía no existe."""
        existentes = {bucket.name for bucket in self.client.storage.list_buckets()}
        if BUCKET_INFORMES not in existentes:
            self.client.storage.create_bucket(BUCKET_INFORMES, options={"public": True})

    def subir_pdf(self, audit_id: str, pdf: bytes) -> str:
        """Sube el informe a Storage, guarda la URL pública y la devuelve."""
        self._asegurar_bucket()
        ruta = f"{audit_id}.pdf"
        self.client.storage.from_(BUCKET_INFORMES).upload(
            ruta, pdf, {"content-type": "application/pdf", "upsert": "true"}
        )
        # get_public_url puede devolver un "?" colgante (querystring vacío)
        url = self.client.storage.from_(BUCKET_INFORMES).get_public_url(ruta).rstrip("?")
        self.client.table("audits").update({"pdf_url": url}).eq("id", audit_id).execute()
        return url
