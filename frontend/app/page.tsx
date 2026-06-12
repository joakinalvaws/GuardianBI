import AuditCard from "@/components/AuditCard";
import { listarAuditorias } from "@/lib/queries";

// Datos de auditoría siempre frescos (sin prerender estático)
export const dynamic = "force-dynamic";

export default async function Home() {
  const audits = await listarAuditorias();

  return (
    <>
      <h1 className="text-2xl font-bold">Auditorías</h1>
      <p className="mt-1 text-sm text-gray-500">
        Cada corrida del agente contrasta los dashboards con la fuente de
        verdad. Entra a una auditoría para ver sus hallazgos.
      </p>

      {audits.length === 0 ? (
        <div className="mt-8 rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-500">
          <p>Todavía no hay auditorías registradas.</p>
          <p className="mt-2">
            Corre <code className="font-mono">python -m app.scheduler --run-now</code>{" "}
            en el backend, y verifica que las políticas de{" "}
            <code className="font-mono">backend/db/policies.sql</code> estén
            aplicadas en Supabase.
          </p>
        </div>
      ) : (
        <div className="mt-6 flex flex-col gap-4">
          {audits.map((audit) => (
            <AuditCard key={audit.id} audit={audit} />
          ))}
        </div>
      )}
    </>
  );
}
