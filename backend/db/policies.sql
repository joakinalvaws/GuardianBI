-- ============================================================
--  Dashboard Guardian — políticas RLS para la web app (Fase 5)
--  Ejecutar TODO el archivo en el SQL Editor del proyecto
--  (supabase-py no corre DDL). Es idempotente: se puede re-correr.
--
--  El frontend lee con la publishable key (rol anon). Las tablas
--  tienen RLS habilitado sin políticas, así que anon ve 0 filas.
--  Estas políticas abren SOLO LECTURA sobre las tablas de auditoría;
--  las tablas de negocio (ventas, sedes, productos) y los snapshots
--  quedan sin exponer.
-- ============================================================

drop policy if exists "lectura publica de auditorias" on audits;
drop policy if exists "lectura publica de hallazgos" on findings;

create policy "lectura publica de auditorias"
  on audits for select
  using (true);

create policy "lectura publica de hallazgos"
  on findings for select
  using (true);

-- Verificación: debe devolver 2 filas (una política por tabla)
select tablename, policyname, roles, cmd
from pg_policies
where tablename in ('audits', 'findings');
