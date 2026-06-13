// Formateo y etiquetas en español — mismas convenciones que el informe PDF
// (backend/app/reports/builder.py).

import type { Severidad, TipoHallazgo } from "./types";

export const SEVERIDAD_LABELS: Record<Severidad, string> = {
  critical: "Crítico",
  warning: "Advertencia",
  ok: "OK",
};

export const ESTADO_LABELS: Record<Severidad, string> = {
  critical: "Atención crítica",
  warning: "Con advertencias",
  ok: "Todo en orden",
};

export const TIPO_LABELS: Record<TipoHallazgo, string> = {
  stale_data: "Datos desactualizados",
  metric_mismatch: "Métrica inconsistente",
  cross_report_conflict: "Conflicto entre reportes",
};

// La DB guarda timestamptz en UTC; la conversión a hora local es solo de display
export const ZONA_HORARIA = "America/Lima";

export function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleString("es-PE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: ZONA_HORARIA,
    hour12: false,
  });
}

export function formatearNumero(valor: number | null): string {
  if (valor === null) return "—";
  return valor.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatearPct(valor: number | null): string {
  if (valor === null) return "—";
  const signo = valor > 0 ? "+" : "";
  return `${signo}${valor.toFixed(1)}%`;
}
