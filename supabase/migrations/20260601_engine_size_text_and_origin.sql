-- Fix avalúos: cilindrada como texto (≤6, admite letras) + columna origen editable.
-- La BD es el PostgreSQL existente del proyecto Supabase; correr este SQL una vez
-- (SQL Editor del Dashboard o psql). Es idempotente / seguro de re-ejecutar.

-- 1) engine_size: NUMERIC(3,1) -> varchar(6). Los valores actuales (ej. 2.5)
--    se conservan como texto ("2.5"). USING castea numérico->texto sin perder datos.
ALTER TABLE vehicle_appraisal
  ALTER COLUMN engine_size TYPE varchar(6) USING engine_size::text;

-- 2) origin: nueva columna de texto libre (ej. MEX/AGE, USA, JAPÓN).
ALTER TABLE vehicle_appraisal
  ADD COLUMN IF NOT EXISTS origin varchar(20);
