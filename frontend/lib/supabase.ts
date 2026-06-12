import { createClient } from "@supabase/supabase-js";

// Publishable key: pública por diseño; RLS limita la lectura a audits y
// findings (ver backend/db/policies.sql).
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
);
