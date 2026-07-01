# ADR-002 — OpenAI Agents SDK en vez de un loop manual sobre chat.completions

Fecha: 2026-06-12 · Estado: aceptada

## Contexto

La auditoría es multi-paso: llamar tools de detección, razonar sobre sus
resultados, clasificar severidad y emitir un resultado estructurado que mapea
1:1 con la base de datos. Hacerlo con `chat.completions` crudo implica escribir
a mano el loop de tool-calling, el parseo/validación de JSON y los reintentos:
pegamento frágil.

## Decisión

Se usa `openai-agents==0.14.0`. `backend/app/agent/guardian.py` declara un
`Agent` con `model=settings.openai_model` (gpt-5.4-mini), tres `function_tool`
(`detect_stale_data`, `check_metric_consistency`, `compare_cross_reports`) y
`output_type=AuditResult` (Pydantic). El SDK gestiona el ciclo de tool-calling
y coacciona la salida al esquema. La convención queda fijada en CLAUDE.md: nada
de `chat.completions` directo.

## Consecuencias

- Salida estructurada y validada (`AuditResult`/`Finding`) que persiste en
  Supabase sin transformación.
- El loop de tool-calling, los reintentos y el enforcement de esquema son
  responsabilidad del SDK, no del código de la app.
- Acoplamiento al Agents SDK; el modelo es configurable vía
  `settings.openai_model`.
- Los tests mockean el `Runner` para probar la orquestación sin llamar a la API
  (`backend/tests/test_agent_flow.py`).
