-- Enable Row-Level Security on all public tables.
-- The Edge Functions use the service_role key which bypasses RLS,
-- so no policies are needed for them to keep working.
-- This blocks direct PostgREST access (anon / authenticated keys).

ALTER TABLE public.vehicle_appraisal ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.appraisal_deductions ENABLE ROW LEVEL SECURITY;
