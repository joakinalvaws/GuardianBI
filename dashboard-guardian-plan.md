# Dashboard Guardian — Plan de proyecto

> Documento de planificación, arquitectura e implementación.  
> Para ejecutar con Claude Code.  
> Versiones verificadas al 11 de junio de 2026.

---

## Contexto y visión del proyecto

### Qué es Dashboard Guardian

Dashboard Guardian es un agente de inteligencia operacional que audita dashboards de Power BI de forma autónoma. El problema que resuelve es real y costoso en cualquier empresa: dashboards desactualizados, KPIs que se contradicen entre reportes, y métricas que llevan días sin cargarse sin que nadie lo haya notado.

La diferencia con las herramientas existentes de data observability (Monte Carlo, Great Expectations, etc.) es el enfoque y el mercado: esas soluciones son enterprise, costosas y auditan pipelines de datos. Dashboard Guardian audita la **capa de visualización** con IA, en lenguaje natural, orientado al segmento pyme/latam donde no existe nada parecido.

### Qué hace el sistema

1. Corre en schedule (cada noche o bajo demanda)
2. Escanea los dashboards de Power BI y los compara contra la fuente de datos original (Supabase/PostgreSQL)
3. Usa un agente GPT-5.4-mini con tool use para diagnosticar tres tipos de problemas: datos desactualizados, métricas inconsistentes y conflictos entre reportes
4. Genera un informe PDF con hallazgos clasificados por severidad (crítico / advertencia / ok) y causa probable redactada en lenguaje natural
5. Notifica por Telegram con un resumen ejecutivo + PDF adjunto, solo cuando hay algo relevante que reportar

### Por qué es relevante para portafolio

- Demuestra arquitectura de agente real con tool use, no un chatbot con datos
- Caso de negocio concreto y medible: "encontré 3 inconsistencias en tus dashboards, aquí están y aquí está la causa"
- Stack moderno y completo: agente IA + backend Python + frontend Next.js + base de datos + notificaciones
- Diferenciador claro frente a herramientas existentes: nadie audita la capa de visualización con IA en el mundo pyme

---

## Stack tecnológico

| Capa | Tecnología | Versión |
|---|---|---|
| Agente IA | GPT-5.4-mini (OpenAI) | `gpt-5.4-mini` |
| Orquestación del agente | OpenAI Agents SDK | `openai-agents==0.14.0` |
| Backend | Python + FastAPI | `3.13` / `0.136.3` |
| Base de datos | Supabase (PostgreSQL) | `supabase==2.31.0` |
| BI | Power BI REST API | simulado en MVP, real en fase final |
| Generación de PDF | WeasyPrint | `69.0` |
| Notificaciones | Telegram Bot API | HTTP directo |
| Email | AWS SES | opcional, fase 2 |
| Frontend | Next.js + Tailwind | `16.2.9` |
| Deploy backend | Railway o Render (MVP) / AWS Lambda (producción) | — |
| Deploy frontend | Vercel | — |
| CI/CD | GitHub Actions | — |
| Scheduler | GitHub Actions programado (MVP) / AWS EventBridge (producción) | — |

> **Nota sobre el Agents SDK:** OpenAI lanzó `openai-agents` como SDK oficial para agentes multi-paso.
> Es más limpio que implementar el loop manualmente con `chat.completions`.
> Lo usamos en lugar de orquestar el tool use a mano — ver sección de arquitectura del agente.

---

## Arquitectura del sistema

```
┌─────────────────────────────────────────────────────────┐
│                     FASE 1 — ESCANEO                    │
│                                                         │
│  Scheduler ──→ Power BI REST API ──→ Supabase           │
│                (o snapshot simulado)   (fuente verdad)  │
└──────────────────────────┬──────────────────────────────┘
                           │
                     Estado actual
                     (métricas + timestamps)
                           │
┌──────────────────────────▼──────────────────────────────┐
│                   FASE 2 — DIAGNÓSTICO                  │
│                                                         │
│      Agente GPT-5.4-mini (OpenAI Agents SDK)            │
│                                                         │
│   detect_stale_data()                                   │
│   check_metric_consistency()                            │
│   compare_cross_reports()                               │
│                                                         │
│              ↓ JSON de hallazgos                        │
│   { severidad, métrica, causa, recomendación }          │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                  FASE 3 — PUBLICACIÓN                   │
│                                                         │
│   PDF (WeasyPrint)   Web App (Next.js)   Telegram Bot   │
│   Descargable        Vista histórica     Resumen + PDF  │
│   Con severidad      Drill-down          Solo si hay    │
│                      Por métrica         hallazgos      │
└─────────────────────────────────────────────────────────┘
```

---

## Estructura del proyecto

```
dashboard-guardian/
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI app, rutas y lifespan
│   │   ├── config.py                 # Settings con pydantic-settings
│   │   ├── scanner/
│   │   │   ├── __init__.py
│   │   │   ├── powerbi_client.py     # Cliente Power BI REST API
│   │   │   ├── source_client.py      # Consultas a Supabase (fuente de verdad)
│   │   │   └── snapshot.py           # Arma el paquete de estado para el agente
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── guardian.py           # Agente con OpenAI Agents SDK
│   │   │   ├── tools.py              # Definición + ejecución de las 3 tools
│   │   │   └── prompts.py            # System prompt del auditor
│   │   ├── reports/
│   │   │   ├── __init__.py
│   │   │   ├── builder.py            # JSON hallazgos → HTML
│   │   │   ├── pdf.py                # WeasyPrint render → PDF
│   │   │   └── templates/
│   │   │       └── informe.html      # Plantilla del informe
│   │   ├── delivery/
│   │   │   ├── __init__.py
│   │   │   ├── telegram.py           # Mensaje + PDF adjunto
│   │   │   └── email.py              # SES (fase 2)
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── models.py             # Tablas: audits, findings, snapshots
│   │   │   └── repository.py         # CRUD de auditorías y hallazgos
│   │   └── scheduler.py              # Trigger manual + cron entry point
│   ├── scripts/
│   │   ├── seed_data.py              # Genera datos de negocio limpios
│   │   └── inject_errors.py          # Rompe datos a propósito para testing
│   ├── tests/
│   │   ├── conftest.py               # Fixtures compartidos
│   │   ├── test_tools.py             # Test unitario por tool
│   │   ├── test_scanner.py           # Test del scanner contra Supabase
│   │   └── test_agent_flow.py        # Flujo end-to-end con agente mockeado
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── page.tsx                  # Lista de auditorías con estado
│   │   ├── audit/[id]/page.tsx       # Detalle: hallazgos + drill-down
│   │   └── metrics/[nombre]/page.tsx # Histórico de salud por métrica
│   ├── components/
│   │   ├── AuditCard.tsx
│   │   ├── FindingBadge.tsx
│   │   └── MetricChart.tsx
│   └── ...
├── docs/
│   └── adr/
│       ├── 001-desacoplar-scanner-de-powerbi.md
│       ├── 002-openai-agents-sdk-sobre-loop-manual.md
│       └── 003-supabase-sobre-excel.md
├── .github/
│   └── workflows/
│       ├── test.yml                  # pytest en cada push
│       └── scheduler.yml             # Cron diario de auditoría
└── README.md
```

---

## Base de datos en Supabase

> **Importante — keys de Supabase:** Los nombres `SUPABASE_KEY` y `SUPABASE_SERVICE_KEY`
> están siendo deprecados. Los nuevos proyectos usan `sb_publishable_xxx` (lectura)
> y `sb_secret_xxx` (escritura). Al crear el proyecto copia las nuevas keys desde
> el panel de conexión.

### Tablas de negocio (fuente de verdad)

```sql
-- Sedes del negocio
create table sedes (
  id serial primary key,
  nombre text not null,
  ciudad text not null
);

-- Catálogo de productos
create table productos (
  id serial primary key,
  nombre text not null,
  categoria text not null,
  costo_unitario numeric(10,2) not null,
  precio_venta numeric(10,2) not null
);

-- Ventas (tabla principal, 6 meses de histórico)
create table ventas (
  id bigserial primary key,
  sede_id int references sedes(id),
  producto_id int references productos(id),
  fecha date not null,
  cantidad int not null,
  monto_total numeric(12,2) not null,
  created_at timestamptz default now()
);

create index idx_ventas_fecha on ventas(fecha);
create index idx_ventas_sede on ventas(sede_id);
```

### Tablas de simulación MVP

```sql
-- Simula lo que Power BI "muestra" en sus dashboards
-- En producción esto se reemplaza por llamadas a la Power BI REST API
-- Ver ADR-001 para la justificación de este desacoplamiento
create table dashboard_snapshots (
  id bigserial primary key,
  reporte text not null,
  metrica text not null,
  valor numeric not null,
  ultima_actualizacion timestamptz not null,
  updated_at timestamptz default now()
);

create unique index idx_snapshot_unico on dashboard_snapshots(reporte, metrica);
```

### Tablas de auditoría (output del guardián)

```sql
-- Registro de cada ejecución del agente
create table audits (
  id uuid primary key default gen_random_uuid(),
  ejecutado_en timestamptz default now(),
  estado text not null default 'running',  -- running | completed | failed
  total_findings int default 0,
  criticos int default 0,
  advertencias int default 0,
  resumen text,
  pdf_url text
);

-- Hallazgos individuales por auditoría
create table findings (
  id uuid primary key default gen_random_uuid(),
  audit_id uuid references audits(id) on delete cascade,
  severidad text not null,           -- critical | warning | ok
  tipo text not null,                -- stale_data | metric_mismatch | cross_report_conflict
  metrica text not null,
  reporte text,
  valor_dashboard numeric,
  valor_fuente numeric,
  diferencia_pct numeric,
  causa_probable text,
  recomendacion text,
  created_at timestamptz default now()
);

create index idx_findings_audit on findings(audit_id);
create index idx_findings_severidad on findings(severidad);
create index idx_findings_metrica on findings(metrica);
```

---

## Variables de entorno

```bash
# .env.example

# OpenAI
OPENAI_API_KEY=sk-...

# Supabase (nuevas keys — formato 2026)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...   # lectura (antes: anon key)
SUPABASE_SECRET_KEY=sb_secret_...             # escritura (antes: service key)

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=tu_chat_id

# Power BI (dejar vacío en MVP, completar en fase final)
POWERBI_TENANT_ID=
POWERBI_CLIENT_ID=
POWERBI_CLIENT_SECRET=
POWERBI_WORKSPACE_ID=

# AWS SES (opcional, fase 2)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
SES_FROM_EMAIL=

# App
ENVIRONMENT=development
AUDIT_SCHEDULE_CRON=0 7 * * *
STALE_DATA_THRESHOLD_HOURS=24
METRIC_TOLERANCE_PCT=1.0
```

---

## El agente con OpenAI Agents SDK

En lugar de implementar el loop de tool use manualmente con `chat.completions`,
usamos el SDK oficial de OpenAI para agentes. Esto simplifica el código y
es lo que el mercado espera ver en 2026.

```python
# agent/guardian.py
from agents import Agent, Runner, function_tool
from .prompts import SYSTEM_PROMPT
from .tools import detect_stale_data, check_metric_consistency, compare_cross_reports

guardian_agent = Agent(
    name="Dashboard Guardian",
    model="gpt-5.4-mini",
    instructions=SYSTEM_PROMPT,
    tools=[
        function_tool(detect_stale_data),
        function_tool(check_metric_consistency),
        function_tool(compare_cross_reports),
    ],
    output_type=AuditResult,   # salida estructurada con Pydantic
)

async def run_audit(snapshot: dict) -> AuditResult:
    result = await Runner.run(
        guardian_agent,
        input=f"Audita este estado de dashboards: {snapshot}"
    )
    return result.final_output
```

### System prompt del agente

```python
# agent/prompts.py

SYSTEM_PROMPT = """
Eres un auditor experto de dashboards de Power BI. Tu trabajo es detectar
problemas en los reportes del negocio de forma sistemática y comunicarlos
con claridad a personas que no son técnicas.

Tienes acceso a tres herramientas de diagnóstico. Para cada auditoría debes:

1. Usar detect_stale_data para identificar métricas desactualizadas
2. Usar check_metric_consistency para cada métrica disponible
3. Usar compare_cross_reports para detectar conflictos entre reportes

Clasifica cada hallazgo con esta severidad:
- critical: dato desactualizado más de 48h, o diferencia mayor al 5%
- warning: desactualización entre 24-48h, o diferencia entre 1-5%
- ok: todo dentro de los parámetros normales

Para cada hallazgo crítico o advertencia, redacta:
- causa_probable: explicación en lenguaje natural, máximo 2 oraciones
- recomendacion: acción concreta que el equipo puede tomar hoy

Cuando no hay hallazgos relevantes, reporta el estado ok con un resumen
positivo. No inventes problemas que las herramientas no hayan confirmado.
"""
```

---

## Scripts de testing

### seed_data.py

Genera datos coherentes de negocio: 3 sedes, 15 productos, 6 meses de
ventas (~5000 filas) y puebla `dashboard_snapshots` con valores correctos
calculados desde `ventas`.

```bash
# Uso
python scripts/seed_data.py
```

### inject_errors.py

Rompe datos a propósito para verificar que cada tool del agente detecta
lo que debe detectar. Cada error mapea 1:1 con una tool del agente.

```bash
# Uso
python scripts/inject_errors.py --error stale_data
python scripts/inject_errors.py --error metric_mismatch
python scripts/inject_errors.py --error cross_report_conflict
python scripts/inject_errors.py --all
python scripts/inject_errors.py --reset   # vuelve a estado limpio
```

---

## Plan de implementación por fases

### Fase 0 — Setup inicial (día 1)

- [ ] Crear repositorio en GitHub con `.gitignore` para Python y Node
- [ ] Crear proyecto en Supabase, copiar URL y nuevas keys (`sb_publishable_` y `sb_secret_`)
- [ ] Crear bot de Telegram con @BotFather, obtener token y chat_id
- [ ] Configurar `.env` local con todas las variables
- [ ] Crear entorno virtual Python 3.13: `python -m venv venv`
- [ ] Instalar dependencias base
- [ ] Verificar conexión a Supabase con un script simple
- [ ] Verificar que el bot de Telegram responde con `sendMessage`

**Criterio de salida:** El bot de Telegram responde a tu chat y Python conecta a Supabase sin errores.

---

### Fase 1 — Base de datos y datos de prueba (días 2-3)

- [ ] Ejecutar el SQL de creación de tablas en Supabase (editor SQL)
- [ ] Escribir e implementar `seed_data.py`
- [ ] Escribir e implementar `inject_errors.py` con los 3 tipos de error
- [ ] Verificar en Supabase Table Editor que los datos se ven correctos

**Criterio de salida:** Puedes romper y reparar los datos con un comando. Los 3 errores son visibles en `dashboard_snapshots`.

---

### Fase 2 — Scanner y snapshot (días 4-5)

- [ ] Implementar `source_client.py`: queries de ventas totales por mes, margen por sede, ventas por producto
- [ ] Implementar `snapshot.py`: arma el paquete de estado (dashboard vs fuente vs timestamps)
- [ ] Tests unitarios en `test_scanner.py` que verifican los valores contra el seed conocido

**Criterio de salida:** `snapshot.py` devuelve un dict con todos los valores necesarios para el agente. Los tests pasan con datos limpios y con datos rotos.

---

### Fase 3 — Agente (días 6-9) ← el corazón del proyecto

- [ ] Instalar `openai-agents` y configurar el agente en `guardian.py`
- [ ] Implementar las 3 tools en `tools.py` con su lógica de consulta a Supabase
- [ ] Definir el modelo Pydantic `AuditResult` para salida estructurada
- [ ] Test con datos limpios: el agente debe reportar todo `ok` sin falsos positivos
- [ ] Test con `--error stale_data`: detecta y clasifica correctamente
- [ ] Test con `--error metric_mismatch`: ídem
- [ ] Test con `--error cross_report_conflict`: ídem
- [ ] Test con `--all`: detecta los 3 simultáneamente

**Criterio de salida:** El ciclo completo funciona desde línea de comandos. El JSON de hallazgos tiene el formato correcto para el render.

---

### Fase 4 — Informes y entrega (días 10-12)

- [ ] Diseñar plantilla HTML del informe (`informe.html`)
- [ ] Implementar `builder.py`: JSON → HTML renderizado
- [ ] Implementar `pdf.py`: HTML → PDF con WeasyPrint 69.0
- [ ] Subir PDF a Supabase Storage, obtener URL pública
- [ ] Implementar `telegram.py`: enviar resumen + PDF con `sendDocument`
- [ ] Implementar `repository.py`: guardar audit y findings en Supabase

**Criterio de salida:** Recibes en Telegram un mensaje con el resumen y el PDF adjunto. Los datos quedan en `audits` y `findings`.

---

### Fase 5 — Web app (días 13-17)

- [ ] Crear proyecto Next.js 16.2.9 con Tailwind
- [ ] Página principal: lista de auditorías con estado y conteo de hallazgos
- [ ] Página de detalle: hallazgos con badge de severidad y drill-down
- [ ] Página de métrica: histórico de salud de una métrica específica
- [ ] Deploy en Vercel conectado al repo

**Criterio de salida:** La web app muestra el historial de auditorías y permite drill-down en cada hallazgo.

---

### Fase 6 — Scheduler y Power BI real (días 18-21)

- [ ] GitHub Action programado (`scheduler.yml`) que llama al endpoint de auditoría
- [ ] Registrar app en Azure AD con permisos de Power BI
- [ ] Crear workspace en Power BI conectado a Supabase vía conector PostgreSQL
- [ ] Implementar `powerbi_client.py` con autenticación OAuth y endpoints reales
- [ ] Reemplazar `dashboard_snapshots` con llamadas reales a `/datasets/{id}/executeQueries`

**Criterio de salida:** El agente audita dashboards reales de Power BI en schedule diario.

---

## Verificación del flujo completo

```bash
# 1. Datos limpios
python scripts/seed_data.py

# 2. Auditoría con datos limpios → debe reportar "todo ok"
python -m app.scheduler --run-now

# 3. Inyectar los 3 tipos de error
python scripts/inject_errors.py --all

# 4. Auditoría con errores → detecta los 3, genera PDF y notifica por Telegram
python -m app.scheduler --run-now

# 5. Verificar en Supabase que audits y findings tienen los registros
# 6. Verificar que el PDF llegó a Telegram
# 7. Verificar que la web app muestra el resultado correctamente
```

---

## Sugerencias para trabajar con Claude Code

### Antes de empezar

Crea un archivo `CLAUDE.md` en la raíz del proyecto. Claude Code lo lee
automáticamente en cada sesión.

```markdown
# CLAUDE.md

## Proyecto
Dashboard Guardian — agente que audita dashboards de Power BI con GPT-5.4-mini.

## Stack
Python 3.13, FastAPI 0.136.3, Supabase 2.31.0 (supabase-py),
OpenAI Agents SDK 0.14.0, WeasyPrint 69.0, Telegram Bot API,
Next.js 16.2.9, pydantic-settings 2.14.1.

## Comandos frecuentes
- Activar entorno: source venv/bin/activate
- Correr backend: fastapi dev app/main.py
- Seed de datos: python scripts/seed_data.py
- Inyectar errores: python scripts/inject_errors.py --all
- Tests: pytest tests/ -v
- Auditoría manual: python -m app.scheduler --run-now

## Convenciones
- Python 3.13, type hints en todas las funciones
- Docstrings en clases y funciones públicas
- Tests para toda función que toque la base de datos o el agente
- Variables de entorno siempre desde config.py, nunca os.environ directo
- Agente con openai-agents SDK, no con chat.completions directo
- Supabase keys nuevas: SUPABASE_PUBLISHABLE_KEY y SUPABASE_SECRET_KEY

## Estructura de carpetas
Ver README.md, sección Estructura del proyecto.
```

### Prompts efectivos para Claude Code por fase

```
"Implementa source_client.py con queries de agregación usando supabase-py 2.31.
Necesito: ventas totales por mes, margen por sede, y ventas por producto.
Incluye tests en test_scanner.py verificando los valores contra el seed."
```

```
"Implementa el agente guardian.py usando openai-agents SDK 0.14.
El agente usa GPT-5.4-mini, tiene las 3 tools definidas en tools.py,
y retorna un AuditResult (Pydantic) como salida estructurada.
Mockea el Runner en los tests para no gastar tokens en CI."
```

```
"Implementa telegram.py con dos funciones: send_summary(text) y
send_report(text, pdf_path) usando la Telegram Bot API directa (httpx).
send_report envía el PDF con sendDocument. Incluye retry con backoff."
```

### ADRs recomendados

- `ADR-001`: Por qué `dashboard_snapshots` desacopla el agente de Azure AD en el MVP
- `ADR-002`: Por qué OpenAI Agents SDK sobre el loop manual de chat.completions
- `ADR-003`: Por qué Supabase sobre Excel o SQLite para el MVP

---

## Dependencias Python

```txt
# requirements.txt
fastapi[standard]==0.136.3
openai-agents==0.14.0
supabase==2.31.0
pydantic-settings==2.14.1
weasyprint==69.0
httpx==0.28.1
python-dotenv==1.1.0
faker==37.0.0
pytest==8.4.0
pytest-asyncio==1.4.0
```

---

## Métricas de éxito del MVP

| Métrica | Objetivo |
|---|---|
| Detección de errores inyectados | 3/3 tipos detectados correctamente |
| Falsos positivos con datos limpios | 0 |
| Tiempo de auditoría completa | < 30 segundos |
| Cobertura de tests en agent/ | > 80% |
| PDF generado y entregado por Telegram | En cada auditoría con hallazgos |

---

*Versiones verificadas al 11 de junio de 2026. Actualizar conforme avance el proyecto.*
