import Link from "next/link";
import { notFound } from "next/navigation";
import FindingBadge from "@/components/FindingBadge";
import {
  ESTADO_LABELS,
  TIPO_LABELS,
  formatearFecha,
  formatearNumero,
  formatearPct,
} from "@/lib/format";
import { obtenerAuditoria } from "@/lib/queries";
import { severidadDeAudit } from "@/lib/types";

export const dynamic = "force-dynamic";

const FONDOS = {
  critical: "border-red-200 bg-red-50",
  warning: "border-amber-200 bg-amber-50",
  ok: "border-green-200 bg-green-50",
};

export default async function AuditDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const datos = await obtenerAuditoria(id);
  if (!datos) notFound();
  const { audit, findings } = datos;
  const severidad = severidadDeAudit(audit);

  return (
    <>
      <Link href="/" className="text-sm text-gray-500 hover:text-gray-800">
        ← Volver a auditorías
      </Link>

      <div className={`mt-4 rounded-lg border p-5 ${FONDOS[severidad]}`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-xl font-bold">
            Auditoría del {formatearFecha(audit.ejecutado_en)}
          </h1>
          <FindingBadge severidad={severidad} label={ESTADO_LABELS[severidad]} />
        </div>
        <p className="mt-2 text-sm text-gray-700">{audit.resumen}</p>
        <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-gray-500">
          <span>
            {audit.total_findings} hallazgo{audit.total_findings !== 1 && "s"} ·{" "}
            {audit.criticos} críticos · {audit.advertencias} advertencias
          </span>
          {audit.pdf_url && (
            <a
              href={audit.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-blue-700 underline hover:text-blue-900"
            >
              Descargar informe PDF
            </a>
          )}
        </div>
      </div>

      <h2 className="mt-8 text-lg font-bold">Hallazgos</h2>

      {findings.length === 0 ? (
        <p className="mt-3 rounded-lg border border-dashed border-green-300 bg-green-50 p-6 text-center text-sm text-green-800">
          Sin hallazgos: todos los dashboards coinciden con la fuente y están
          actualizados.
        </p>
      ) : (
        <div className="mt-3 flex flex-col gap-4">
          {findings.map((f) => (
            <article
              key={f.id}
              className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-center gap-2">
                <FindingBadge severidad={f.severidad} />
                <h3 className="font-semibold">{TIPO_LABELS[f.tipo]}</h3>
                <span className="text-gray-400">·</span>
                <Link
                  href={`/metrics/${encodeURIComponent(f.metrica)}`}
                  className="font-mono text-sm text-blue-700 underline hover:text-blue-900"
                >
                  {f.metrica}
                </Link>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                {f.reporte ?? "Afecta a varios reportes"}
              </p>

              <dl className="mt-3 grid grid-cols-3 gap-2 rounded-md bg-gray-50 p-3 text-sm">
                <div>
                  <dt className="text-xs text-gray-500">Valor en el dashboard</dt>
                  <dd className="font-mono">{formatearNumero(f.valor_dashboard)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Valor en la fuente</dt>
                  <dd className="font-mono">{formatearNumero(f.valor_fuente)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Diferencia</dt>
                  <dd className="font-mono">{formatearPct(f.diferencia_pct)}</dd>
                </div>
              </dl>

              <div className="mt-3 text-sm">
                <p>
                  <span className="font-semibold">Causa probable:</span>{" "}
                  {f.causa_probable}
                </p>
                <p className="mt-1">
                  <span className="font-semibold">Recomendación:</span>{" "}
                  {f.recomendacion}
                </p>
              </div>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
