"""Tests de integración de AuditRepository contra Supabase.

Cada test limpia sus propios registros al salir (borrar el audit
cascadea a findings por la FK on delete cascade).
"""

import pytest

from app.db.repository import BUCKET_INFORMES, AuditRepository


@pytest.fixture
def repo(client) -> AuditRepository:
    return AuditRepository(client)


@pytest.fixture
def audit_id(repo, client):
    """Auditoría recién creada; se borra (con sus findings) al terminar."""
    audit_id = repo.crear_auditoria()
    yield audit_id
    client.table("audits").delete().eq("id", audit_id).execute()


def _audit(client, audit_id: str) -> dict:
    return client.table("audits").select("*").eq("id", audit_id).execute().data[0]


def test_crear_auditoria_queda_en_running(client, audit_id) -> None:
    fila = _audit(client, audit_id)
    assert fila["estado"] == "running"
    assert fila["total_findings"] == 0
    assert fila["pdf_url"] is None


def test_guardar_resultado_persiste_audit_y_findings(
    repo, client, audit_id, resultado_critico
) -> None:
    repo.guardar_resultado(audit_id, resultado_critico)

    fila = _audit(client, audit_id)
    assert fila["estado"] == "completed"
    assert fila["total_findings"] == 2
    assert fila["criticos"] == 1
    assert fila["advertencias"] == 1
    assert fila["resumen"] == resultado_critico.resumen

    findings = (
        client.table("findings").select("*").eq("audit_id", audit_id).order("severidad").execute().data
    )
    assert len(findings) == 2
    critico = next(f for f in findings if f["severidad"] == "critical")
    assert critico["tipo"] == "stale_data"
    assert critico["metrica"] == "margen_lima"
    assert critico["valor_dashboard"] is None
    advertencia = next(f for f in findings if f["severidad"] == "warning")
    assert advertencia["diferencia_pct"] == 12.0


def test_guardar_resultado_sin_findings_no_inserta_filas(
    repo, client, audit_id, resultado_limpio
) -> None:
    repo.guardar_resultado(audit_id, resultado_limpio)

    fila = _audit(client, audit_id)
    assert fila["estado"] == "completed"
    assert fila["total_findings"] == 0
    findings = client.table("findings").select("id").eq("audit_id", audit_id).execute().data
    assert findings == []


def test_marcar_fallida_guarda_el_error(repo, client, audit_id) -> None:
    repo.marcar_fallida(audit_id, "timeout del agente")

    fila = _audit(client, audit_id)
    assert fila["estado"] == "failed"
    assert fila["resumen"] == "Error: timeout del agente"


def test_subir_pdf_publica_y_guarda_url(repo, client, audit_id) -> None:
    try:
        url = repo.subir_pdf(audit_id, b"%PDF-1.7 contenido de prueba")

        assert audit_id in url
        assert BUCKET_INFORMES in url
        assert not url.endswith("?")
        assert _audit(client, audit_id)["pdf_url"] == url
    finally:
        client.storage.from_(BUCKET_INFORMES).remove([f"{audit_id}.pdf"])
