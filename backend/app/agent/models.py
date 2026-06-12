"""Salida estructurada del agente auditor (output_type del Agents SDK).

`Finding` espeja las columnas de la tabla `findings` para que en Fase 4
el repository pueda guardar los hallazgos sin transformaciones.

Nota: sin defaults en los campos — el modo strict de structured outputs
exige que todos los campos sean requeridos (los nullables van como
`tipo | None` sin default).
"""

from typing import Literal

from pydantic import BaseModel, Field

Severidad = Literal["critical", "warning", "ok"]
TipoHallazgo = Literal["stale_data", "metric_mismatch", "cross_report_conflict"]


class Finding(BaseModel):
    """Un hallazgo individual de la auditoría."""

    severidad: Severidad
    tipo: TipoHallazgo
    metrica: str
    reporte: str | None = Field(
        description="Reporte afectado; null si el hallazgo involucra varios reportes"
    )
    valor_dashboard: float | None
    valor_fuente: float | None
    diferencia_pct: float | None
    causa_probable: str = Field(description="Explicación en lenguaje natural, máximo 2 oraciones")
    recomendacion: str = Field(description="Acción concreta que el equipo puede tomar hoy")


class AuditResult(BaseModel):
    """Resultado completo de una corrida del agente auditor."""

    estado_general: Severidad
    resumen: str = Field(
        description="Resumen ejecutivo en 2-3 oraciones para una persona no técnica"
    )
    findings: list[Finding]
