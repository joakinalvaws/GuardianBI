"""Agente auditor de dashboards con OpenAI Agents SDK.

Ciclo completo desde línea de comandos (requiere venv activo y datos seedeados):

    cd backend && python -m app.agent.guardian
"""

import asyncio
import json

from agents import Agent, Runner, function_tool, set_default_openai_key, set_tracing_disabled

from app.agent.models import AuditResult
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import check_metric_consistency, compare_cross_reports, detect_stale_data
from app.config import settings

# El SDK lee OPENAI_API_KEY del entorno; nuestra convención es config.py
set_default_openai_key(settings.openai_api_key)
# El exporter de traces del SDK 0.14 manda un parámetro que el backend
# de OpenAI rechaza (400 usage.requests) — apagado hasta actualizar el SDK
set_tracing_disabled(True)

guardian_agent = Agent(
    name="Dashboard Guardian",
    model=settings.openai_model,
    instructions=SYSTEM_PROMPT,
    tools=[
        function_tool(detect_stale_data),
        function_tool(check_metric_consistency),
        function_tool(compare_cross_reports),
    ],
    output_type=AuditResult,
)


async def run_audit(snapshot: dict) -> AuditResult:
    """Corre la auditoría completa sobre el paquete de estado del scanner."""
    result = await Runner.run(
        guardian_agent,
        input=f"Audita este estado de dashboards: {snapshot}",
    )
    return result.final_output


def main() -> int:
    """Ciclo manual: scanner → agente → JSON de hallazgos por stdout."""
    from app.scanner.snapshot import build_audit_package

    print("→ Armando paquete de estado (scanner)…")
    paquete = build_audit_package()
    print(f"→ Auditando con {settings.openai_model}…\n")
    resultado = asyncio.run(run_audit(paquete))
    print(json.dumps(resultado.model_dump(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
