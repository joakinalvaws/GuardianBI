// Tipos que espejan las tablas audits y findings de Supabase
// (ver backend/db/schema.sql).

export type Severidad = "critical" | "warning" | "ok";

export type TipoHallazgo =
  | "stale_data"
  | "metric_mismatch"
  | "cross_report_conflict";

export interface Audit {
  id: string;
  ejecutado_en: string;
  estado: "running" | "completed" | "failed";
  total_findings: number;
  criticos: number;
  advertencias: number;
  resumen: string | null;
  pdf_url: string | null;
}

export interface Finding {
  id: string;
  audit_id: string;
  severidad: Severidad;
  tipo: TipoHallazgo;
  metrica: string;
  reporte: string | null;
  valor_dashboard: number | null;
  valor_fuente: number | null;
  diferencia_pct: number | null;
  causa_probable: string | null;
  recomendacion: string | null;
  created_at: string;
}

// Finding con la fecha de su auditoría (join para el histórico por métrica)
export interface FindingConFecha extends Finding {
  audits: { ejecutado_en: string };
}

/** Severidad efectiva de una auditoría, derivada de sus conteos. */
export function severidadDeAudit(audit: Audit): Severidad {
  if (audit.criticos > 0) return "critical";
  if (audit.advertencias > 0) return "warning";
  return "ok";
}
