import Link from "next/link";
import type { Audit } from "@/lib/types";
import { severidadDeAudit } from "@/lib/types";
import { ESTADO_LABELS, formatearFecha } from "@/lib/format";
import FindingBadge from "./FindingBadge";

const BORDES = {
  critical: "border-l-red-600",
  warning: "border-l-amber-500",
  ok: "border-l-green-600",
};

export default function AuditCard({ audit }: { audit: Audit }) {
  const severidad = severidadDeAudit(audit);
  const fallida = audit.estado === "failed";

  return (
    <Link
      href={`/audit/${audit.id}`}
      className={`block rounded-lg border border-l-4 border-gray-200 bg-white p-5 shadow-sm transition hover:shadow-md ${
        fallida ? "border-l-gray-400" : BORDES[severidad]
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <time className="text-sm text-gray-500">
          {formatearFecha(audit.ejecutado_en)} UTC
        </time>
        {fallida ? (
          <span className="inline-block rounded-full bg-gray-500 px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide text-white">
            Fallida
          </span>
        ) : (
          <FindingBadge severidad={severidad} label={ESTADO_LABELS[severidad]} />
        )}
      </div>

      <p className="mt-2 line-clamp-2 text-sm text-gray-700">
        {audit.resumen ?? "Sin resumen."}
      </p>

      <p className="mt-3 text-xs text-gray-500">
        {audit.total_findings} hallazgo{audit.total_findings !== 1 && "s"} ·{" "}
        <span className="font-medium text-red-700">{audit.criticos} críticos</span> ·{" "}
        <span className="font-medium text-amber-700">
          {audit.advertencias} advertencias
        </span>
      </p>
    </Link>
  );
}
