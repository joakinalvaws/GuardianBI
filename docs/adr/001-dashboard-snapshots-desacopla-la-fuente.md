# ADR-001 — dashboard_snapshots como capa de abstracción de la fuente de dashboards

Fecha: 2026-06-11 · Estado: aceptada

## Contexto

Para auditar hay que comparar "lo que muestra el dashboard" contra la fuente de
verdad. Obtener esos valores desde Power BI real exige registrar una app en
Azure AD, un service principal o flujo ROPC y licencias de Microsoft: fricción
que bloquea el desarrollo y hace imposible una demo pública indefinida.

El agente y sus tools solo necesitan un contrato de datos ("qué reporte, qué
métrica, qué valor y cuándo se actualizó"), no la tecnología concreta que los
produce.

## Decisión

Se introduce la tabla `dashboard_snapshots` (reporte, metrica, valor,
ultima_actualizacion) como abstracción de "lo que muestra el dashboard". El
scanner (`backend/app/scanner/snapshot.py`) lee de esa tabla y arma el paquete
de auditoría; el agente nunca habla con Azure AD. Power BI real queda como una
implementación intercambiable detrás del mismo contrato
(`backend/app/scanner/powerbi_client.py`, flag `use_real_powerbi`).

## Consecuencias

- Desarrollo y demo pública sin licencias de Microsoft.
- La lógica del agente y las tools es idéntica en MVP y en producción: el
  paquete de auditoría tiene la misma forma.
- `scripts/inject_errors.py` puede corromper snapshots de forma determinista
  para validar la detección de forma reproducible.
- En el MVP hay que mantener los snapshots en sync con la fuente
  (`scripts/seed_data.py`); la ruta de adopción de Power BI real se documenta
  en el ADR-005.
