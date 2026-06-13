import type { FindingConFecha } from "@/lib/types";
import { ZONA_HORARIA, formatearFecha, formatearPct } from "@/lib/format";

const COLORES = {
  critical: "fill-red-600",
  warning: "fill-amber-500",
  ok: "fill-green-600",
};

const ALTO = 180;
const ANCHO_BARRA = 40;
const ESPACIO = 16;
const MARGEN_INFERIOR = 24;
// Altura mínima visible para hallazgos sin diferencia numérica (stale_data)
const ALTO_MINIMO = 8;

/**
 * Histórico de desviaciones de una métrica: una barra por hallazgo,
 * altura = |diferencia_pct|, color = severidad. SVG puro, sin librerías.
 */
export default function MetricChart({
  findings,
}: {
  findings: FindingConFecha[];
}) {
  const maxPct = Math.max(
    ...findings.map((f) => Math.abs(f.diferencia_pct ?? 0)),
    1,
  );
  const ancho = findings.length * (ANCHO_BARRA + ESPACIO) + ESPACIO;
  const altoUtil = ALTO - MARGEN_INFERIOR - 20;

  return (
    <svg
      viewBox={`0 0 ${ancho} ${ALTO}`}
      className="w-full max-w-2xl"
      role="img"
      aria-label="Histórico de desviaciones de la métrica"
    >
      {findings.map((f, i) => {
        const pct = Math.abs(f.diferencia_pct ?? 0);
        const altoBarra = Math.max((pct / maxPct) * altoUtil, ALTO_MINIMO);
        const x = ESPACIO + i * (ANCHO_BARRA + ESPACIO);
        const y = ALTO - MARGEN_INFERIOR - altoBarra;
        return (
          <g key={f.id}>
            <text
              x={x + ANCHO_BARRA / 2}
              y={y - 6}
              textAnchor="middle"
              className="fill-gray-700 text-[11px] font-semibold"
            >
              {f.diferencia_pct === null ? "s/d" : formatearPct(f.diferencia_pct)}
            </text>
            <rect
              x={x}
              y={y}
              width={ANCHO_BARRA}
              height={altoBarra}
              rx={3}
              className={COLORES[f.severidad]}
            >
              <title>
                {formatearFecha(f.audits.ejecutado_en)} ·{" "}
                {formatearPct(f.diferencia_pct)}
              </title>
            </rect>
            <text
              x={x + ANCHO_BARRA / 2}
              y={ALTO - 8}
              textAnchor="middle"
              className="fill-gray-500 text-[10px]"
            >
              {new Date(f.audits.ejecutado_en).toLocaleDateString("es-PE", {
                day: "2-digit",
                month: "short",
                timeZone: ZONA_HORARIA,
              })}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
