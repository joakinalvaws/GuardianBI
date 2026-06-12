# ADR-005 — Power BI real como ruta de producción documentada

Fecha: 2026-06-12 · Estado: aceptada

## Contexto

La integración con Power BI REST API requiere tenant organizacional
de Microsoft Entra ID y licencia Fabric. Para un portafolio personal
esto introduce una dependencia con fecha de vencimiento (60 días de
trial) y cuentas de pago de terceros.

## Decisión

Mantener `dashboard_snapshots` como capa de abstracción del scanner.
La integración real está documentada en `docs/powerbi-production.md`
y el código en `backend/app/scanner/powerbi_client.py` está preparado
para conectarse cuando el entorno lo permita (autenticación por client
credentials y consultas DAX vía `executeQueries`, con tests mockeados).

## Consecuencias

El proyecto es demostrable indefinidamente sin depender de licencias
de terceros. La arquitectura desacoplada (ADR-001) hace que enchufar
Power BI real sea un cambio de implementación, no de diseño: las
métricas que hoy se leen de `dashboard_snapshots` pasarían a leerse
con `PowerBIClient.execute_dax()` sin tocar el agente ni sus tools.
