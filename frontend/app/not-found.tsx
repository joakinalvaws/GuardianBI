import Link from "next/link";

export default function NotFound() {
  return (
    <div className="py-16 text-center">
      <h1 className="text-2xl font-bold">No encontrado</h1>
      <p className="mt-2 text-sm text-gray-500">
        La auditoría o métrica que buscas no existe (o las políticas de lectura
        aún no están aplicadas en Supabase).
      </p>
      <Link
        href="/"
        className="mt-4 inline-block text-blue-700 underline hover:text-blue-900"
      >
        ← Volver a auditorías
      </Link>
    </div>
  );
}
