# Dashboard Guardian

Agente de inteligencia operacional que audita dashboards de Power BI de forma autónoma.

Detecta tres tipos de problemas que cuestan dinero y nadie nota a tiempo:

1. **Datos desactualizados** — métricas que llevan días sin cargarse
2. **Métricas inconsistentes** — el dashboard dice una cosa, la fuente de datos otra
3. **Conflictos entre reportes** — la misma métrica con valores distintos en dos reportes

Cuando encuentra algo, genera un informe PDF con severidad y causa probable en lenguaje
natural, y lo envía por Telegram. Solo notifica cuando hay algo relevante.

## Arquitectura

```
Scheduler → Scanner (Power BI / snapshots + Supabase) → Agente GPT-5.4-mini (3 tools)
          → JSON de hallazgos → PDF (WeasyPrint) + Telegram + Web app (Next.js)
```

El agente usa el **OpenAI Agents SDK** con tool use real: `detect_stale_data`,
`check_metric_consistency` y `compare_cross_reports`.

## Stack

| Capa | Tecnología |
|---|---|
| Agente IA | GPT-5.4-mini + OpenAI Agents SDK |
| Backend | Python 3.12 + FastAPI |
| Base de datos | Supabase (PostgreSQL) |
| PDF | WeasyPrint |
| Notificaciones | Telegram Bot API |
| Frontend | Next.js + Tailwind |

## Setup rápido

```bash
# 1. Entorno
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt

# 2. Credenciales
cp backend/.env.example backend/.env   # y rellena los valores reales

# 3. Verificar conexiones
python backend/scripts/check_supabase.py
python backend/scripts/check_openai.py
python backend/scripts/check_telegram.py

# 4. Base de datos: ejecutar backend/db/schema.sql en el SQL Editor de Supabase

# 5. Datos de prueba
python backend/scripts/seed_data.py
python backend/scripts/inject_errors.py --all     # romper datos a propósito
python backend/scripts/inject_errors.py --reset   # volver a estado limpio
```

## Documentación

- Plan completo, fases y criterios de salida: [`dashboard-guardian-plan.md`](dashboard-guardian-plan.md)
- Decisiones de arquitectura: [`docs/adr/`](docs/adr/)
