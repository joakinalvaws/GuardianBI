-- ============================================================
--  Dashboard Guardian — esquema de base de datos (Supabase)
--  Ejecutar en el SQL Editor del proyecto (supabase-py no corre DDL).
--  Fuente: dashboard-guardian-plan.md, sección "Base de datos en Supabase"
-- ============================================================

-- ----------------------------------------------------------------
-- Tablas de negocio (fuente de verdad)
-- ----------------------------------------------------------------

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

-- ----------------------------------------------------------------
-- Tablas de simulación MVP
-- ----------------------------------------------------------------

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

-- ----------------------------------------------------------------
-- Tablas de auditoría (output del guardián)
-- ----------------------------------------------------------------

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
