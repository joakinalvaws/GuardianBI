# CLAUDE.md

## Proyecto
Dashboard Guardian — agente que audita dashboards de Power BI con GPT-5.4-mini.
Detecta datos desactualizados, métricas inconsistentes y conflictos entre reportes;
genera informe PDF y notifica por Telegram.

Plan completo del proyecto: `dashboard-guardian-plan.md` (fases, arquitectura, SQL, criterios de salida).

## Stack
Python 3.12, FastAPI 0.136.3, Supabase 2.31.0 (supabase-py),
OpenAI Agents SDK 0.14.0, WeasyPrint 69.0, Telegram Bot API,
Next.js 16.2.9, pydantic-settings 2.14.1.

## Comandos frecuentes
- Activar entorno: `source backend/venv/bin/activate`
- Correr backend: `cd backend && fastapi dev app/main.py`
- Seed de datos: `python backend/scripts/seed_data.py`
- Inyectar errores: `python backend/scripts/inject_errors.py --all`
- Reset de datos: `python backend/scripts/inject_errors.py --reset`
- Tests: `cd backend && pytest tests/ -v`
- Auditoría manual: `cd backend && python -m app.scheduler --run-now`

## Convenciones
- Python 3.12, type hints en todas las funciones
- Docstrings en clases y funciones públicas
- Tests para toda función que toque la base de datos o el agente
- Variables de entorno siempre desde `app/config.py`, nunca `os.environ` directo
- Agente con openai-agents SDK, no con chat.completions directo
- Supabase: `SUPABASE_PUBLISHABLE_KEY` (lectura/frontend) y `SUPABASE_SECRET_KEY` (escritura/backend)
- Los secretos viven solo en `backend/.env` (gitignored); `backend/.env.example` lleva placeholders

## Estructura
- `backend/app/` — scanner/, agent/, reports/, delivery/, db/, config.py, main.py
- `backend/scripts/` — seed_data.py, inject_errors.py, check_*.py
- `backend/db/schema.sql` — DDL para correr en el SQL Editor de Supabase (supabase-py no ejecuta DDL)
- `frontend/` — Next.js (Fase 5)
- `docs/adr/` — decisiones de arquitectura

## Estado / fases
Implementación por fases (ver plan). Fase 0 = setup y verificación de conexiones;
Fase 1 = DB + seed + inject_errors; Fase 2 = scanner; Fase 3 = agente (núcleo);
Fase 4 = PDF + Telegram; Fase 5 = web; Fase 6 = scheduler + Power BI real.
No saltarse fases ni criterios de salida.
