-- Enable RLS on mi_tabla to fix Supabase security alert.
-- Edge Functions use service_role key (bypasses RLS) so they are unaffected.
ALTER TABLE public.mi_tabla ENABLE ROW LEVEL SECURITY;
