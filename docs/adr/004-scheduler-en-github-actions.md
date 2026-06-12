# ADR-004 — Scheduler en GitHub Actions en vez de endpoint desplegado

Fecha: 2026-06-12 · Estado: aceptada

## Contexto

El plan original de la Fase 6 proponía un GitHub Action programado que
llamara a un endpoint HTTP de auditoría, lo que implicaba desplegar el
backend FastAPI en Railway/Render: una cuenta más, un servicio que mantener
despierto (los free tiers duermen) y secretos duplicados en otra plataforma.

El ciclo de auditoría (`python -m app.scheduler --run-now`) no necesita
estar "siempre encendido": corre una vez al día, tarda ~1 minuto y todas
sus dependencias externas (Supabase, OpenAI, Telegram) son APIs.

## Decisión

El workflow `scheduler.yml` corre la auditoría **directamente en el runner**
de GitHub Actions: checkout del repo, Python 3.12, `pip install` y
`python -m app.scheduler --run-now`, con los secretos en GitHub Actions
Secrets. Sin backend desplegado.

## Consecuencias

- Cero infraestructura propia; los logs de cada corrida quedan en la
  pestaña Actions del repo.
- Costo: ~3 min/día de runner (~90 min/mes, dentro de los 2000 gratuitos
  de repos privados).
- GitHub desactiva los crons tras 60 días sin actividad en el repo — un
  commit o un disparo manual los reactiva.
- Si en el futuro la web necesita disparar auditorías on-demand, ahí sí
  habrá que desplegar el backend (o usar `workflow_dispatch` vía API).
