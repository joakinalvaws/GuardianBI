# ADR-003 — Supabase (PostgreSQL) en vez de Excel o SQLite para el MVP

Fecha: 2026-06-11 · Estado: aceptada

## Contexto

El proyecto necesita almacenar la fuente de verdad del negocio
(ventas/productos/sedes), los snapshots de dashboards y el rastro de auditoría
(audits/findings + PDFs), y además que una web lea las auditorías. Un Excel/CSV
o un SQLite local no serían alcanzables a la vez por un runner de GitHub Actions
y un frontend en Vercel, ni ofrecen agregación SQL, índices, almacenamiento de
objetos o control de acceso por fila.

## Decisión

Supabase (PostgreSQL gestionado). `backend/db/schema.sql` define 6 tablas +
índices; los PDFs van a Supabase Storage; la web lee con la publishable key y
RLS de solo lectura (`backend/db/policies.sql`). El backend escribe con la
secret key; el frontend solo lee `audits`/`findings`. Free tier, sin servidor
propio que mantener.

## Consecuencias

- Una sola base compartida, alcanzable por el scheduler serverless (Actions) y
  por el frontend (Vercel).
- Agregación SQL real sobre `ventas` para la fuente de verdad; índices para el
  rendimiento de las consultas.
- Storage de objetos para los enlaces públicos a PDF; RLS mantiene las tablas de
  negocio ocultas a la web.
- El DDL se corre en el SQL Editor de Supabase (supabase-py no ejecuta DDL): un
  paso de setup manual.
