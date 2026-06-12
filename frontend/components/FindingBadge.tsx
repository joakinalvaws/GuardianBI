import type { Severidad } from "@/lib/types";
import { SEVERIDAD_LABELS } from "@/lib/format";

const ESTILOS: Record<Severidad, string> = {
  critical: "bg-red-600 text-white",
  warning: "bg-amber-500 text-white",
  ok: "bg-green-600 text-white",
};

export default function FindingBadge({
  severidad,
  label,
}: {
  severidad: Severidad;
  label?: string;
}) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide ${ESTILOS[severidad]}`}
    >
      {label ?? SEVERIDAD_LABELS[severidad]}
    </span>
  );
}
