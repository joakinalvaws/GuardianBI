import Link from "next/link";
import FindingBadge from "@/components/FindingBadge";
import MetricChart from "@/components/MetricChart";
import { TIPO_LABELS, formatearFecha, formatearPct } from "@/lib/format";
import { contarAuditorias, historicoMetrica } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function MetricHistory({
  params,
}: {
  params: Promise<{ nombre: string }>;
}) {
  const { nombre } = await params;
  const metrica = decodeURIComponent(nombre);
  const [findings, totalAudits] = await Promise.all([
    historicoMetrica(metrica),
    contarAuditorias(),
  ]);

  return (
    <>
      <Link href="/" className="text-sm text-gray-500 hover:text-gray-800">
        ← Volver a auditorías
      </Link>

      <h1 className="mt-4 text-2xl font-bold">
        Métrica: <span className="font-mono">{metrica}</span>
      </h1>
      <p className="mt-1 text-sm text-gray-500">
        {findings.length} hallazgo{findings.length !== 1 && "s"} en {totalAudits}{" "}
        auditoría{totalAudits !== 1 && "s"} — una métrica sana no aparece en
        ningún hallazgo.
      </p>

      {findings.length === 0 ? (
        <p className="mt-8 rounded-lg border border-dashed border-green-300 bg-green-50 p-6 text-center text-sm text-green-800">
          Sin hallazgos históricos para esta métrica.
        </p>
      ) : (
        <>
          <section className="mt-6 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700">
              Desviación detectada por auditoría
            </h2>
            <div className="mt-4">
              <MetricChart findings={findings} />
            </div>
          </section>

          <section className="mt-6">
            <h2 className="text-lg font-bold">Detalle de hallazgos</h2>
            <div className="mt-3 overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-left text-xs text-gray-500">
                  <tr>
                    <th className="px-4 py-2 font-medium">Fecha (UTC)</th>
                    <th className="px-4 py-2 font-medium">Severidad</th>
                    <th className="px-4 py-2 font-medium">Tipo</th>
                    <th className="px-4 py-2 font-medium">Reporte</th>
                    <th className="px-4 py-2 text-right font-medium">Diferencia</th>
                    <th className="px-4 py-2 font-medium"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {findings.map((f) => (
                    <tr key={f.id}>
                      <td className="px-4 py-2 whitespace-nowrap">
                        {formatearFecha(f.audits.ejecutado_en)}
                      </td>
                      <td className="px-4 py-2">
                        <FindingBadge severidad={f.severidad} />
                      </td>
                      <td className="px-4 py-2">{TIPO_LABELS[f.tipo]}</td>
                      <td className="px-4 py-2 text-gray-500">
                        {f.reporte ?? "Varios"}
                      </td>
                      <td className="px-4 py-2 text-right font-mono">
                        {formatearPct(f.diferencia_pct)}
                      </td>
                      <td className="px-4 py-2">
                        <Link
                          href={`/audit/${f.audit_id}`}
                          className="text-blue-700 underline hover:text-blue-900"
                        >
                          Ver auditoría
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  );
}
