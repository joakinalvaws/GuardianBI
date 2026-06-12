import { supabase } from "./supabase";
import type { Audit, Finding, FindingConFecha } from "./types";

export async function listarAuditorias(): Promise<Audit[]> {
  const { data, error } = await supabase
    .from("audits")
    .select("*")
    .order("ejecutado_en", { ascending: false });
  if (error) throw new Error(`Error leyendo audits: ${error.message}`);
  return data;
}

export async function obtenerAuditoria(
  id: string,
): Promise<{ audit: Audit; findings: Finding[] } | null> {
  const { data: audit, error } = await supabase
    .from("audits")
    .select("*")
    .eq("id", id)
    .maybeSingle();
  if (error) throw new Error(`Error leyendo la auditoría: ${error.message}`);
  if (!audit) return null;

  const { data: findings, error: errorFindings } = await supabase
    .from("findings")
    .select("*")
    .eq("audit_id", id)
    .order("severidad") // critical < warning (orden alfabético ascendente)
    .order("created_at");
  if (errorFindings)
    throw new Error(`Error leyendo hallazgos: ${errorFindings.message}`);

  return { audit, findings };
}

/** Hallazgos históricos de una métrica con la fecha de cada auditoría. */
export async function historicoMetrica(
  metrica: string,
): Promise<FindingConFecha[]> {
  const { data, error } = await supabase
    .from("findings")
    .select("*, audits!inner(ejecutado_en)")
    .eq("metrica", metrica)
    .order("created_at", { ascending: true });
  if (error)
    throw new Error(`Error leyendo el histórico de la métrica: ${error.message}`);
  return data as FindingConFecha[];
}

/** Total de auditorías corridas (para contextualizar el histórico). */
export async function contarAuditorias(): Promise<number> {
  const { count, error } = await supabase
    .from("audits")
    .select("id", { count: "exact", head: true });
  if (error) throw new Error(`Error contando auditorías: ${error.message}`);
  return count ?? 0;
}
