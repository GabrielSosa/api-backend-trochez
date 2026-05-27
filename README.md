# Migración FastAPI → Supabase Edge Functions

Sustituye el backend `api-backend-trochez.fly.dev` por funciones Deno/TypeScript
desplegadas en Supabase. La base de datos (PostgreSQL en el mismo proyecto Supabase)
no cambia — sólo cambia quién la consulta.

## 1. Estructura

```
supabase/
  config.toml
  functions/
    deno.json
    _shared/
      auth.ts      — verify JWT (HS256) + cargar usuario
      cors.ts      — CORS y helpers de respuesta
      db.ts        — cliente Supabase (service_role)
      hash.ts      — bcryptjs (compatible con hashes de passlib/bcrypt)
    api-security-signin/    — POST login
    api-security-signup/    — POST crear usuario (requiere auth)
    api-users/              — GET list, GET/PUT/DELETE /{id}
    api-appraisals/         — GET list, GET /search, GET/PUT/DELETE /{id}, POST
    api-dashboard/          — /summary, /ventas-dia, /ventas-mes, /carros-mas-avaluos
    certificates-appraisal/ — GET /{id} (HTML printable; ?format=json para JSON)
.github/workflows/deploy-functions.yml
```

## 2. Secrets que hay que configurar

### GitHub repo secrets (Settings → Secrets and variables → Actions)

| Nombre | Valor |
| --- | --- |
| `SUPABASE_ACCESS_TOKEN` | Token personal generado en https://supabase.com/dashboard/account/tokens |

### Supabase Edge Function secrets

```bash
supabase secrets set --project-ref owgqfjxswaxwwwgkrbmq \
  SUPABASE_URL="https://owgqfjxswaxwwwgkrbmq.supabase.co" \
  SUPABASE_SERVICE_ROLE_KEY="<service_role_key>" \
  JWT_SECRET="<mismo SECRET_KEY que usaba FastAPI>"
```

> El `JWT_SECRET` **debe** coincidir con el `SECRET_KEY` que estaba en Fly.io;
> de lo contrario, todos los usuarios deberán hacer login otra vez.

## 3. Deploy manual (primera vez o para probar)

```bash
brew install supabase/tap/supabase   # o: npm i -g supabase
supabase login                       # usa el access token
supabase link --project-ref owgqfjxswaxwwwgkrbmq
supabase functions deploy api-security-signin --no-verify-jwt
# … repetir para cada función, o ejecutar el workflow manualmente
```

## 4. Deploy automático

Cada push a `main` que toque `supabase/functions/**` ejecuta
`.github/workflows/deploy-functions.yml`, que despliega todas las funciones en
paralelo. Se puede también disparar manualmente desde la pestaña Actions
(workflow_dispatch).

## 5. Cambio en el frontend (SvelteKit)

Editar **`src/lib/constants.js`** del repo del frontend:

```js
// ANTES
export const API_BASE_URL = 'https://api-backend-trochez.fly.dev';
// DESPUÉS
export const API_BASE_URL = 'https://owgqfjxswaxwwwgkrbmq.supabase.co/functions/v1';
```

⚠️ **Importante sobre las rutas**: el FastAPI exponía rutas con prefijos
`/api/security/signin`, `/api/users/{id}`, etc. Las Edge Functions son una por
URL pública (`/functions/v1/<function-name>`), así que el frontend debe llamar:

| Endpoint anterior | Endpoint nuevo |
| --- | --- |
| `POST /api/security/signin` | `POST /api-security-signin` |
| `POST /api/security/signup` | `POST /api-security-signup` |
| `GET /api/users` / `GET /api/users/{id}` | `GET /api-users` / `GET /api-users/{id}` |
| `GET /api/appraisals/` | `GET /api-appraisals` |
| `GET /api/appraisals/{id}/` | `GET /api-appraisals/{id}` |
| `POST /api/appraisals/` | `POST /api-appraisals` |
| `PUT /api/appraisals/{id}/` | `PUT /api-appraisals/{id}` |
| `DELETE /api/appraisals/{id}/` | `DELETE /api-appraisals/{id}` |
| `GET /api/appraisals/search/?q=...` | `GET /api-appraisals/search?q=...` |
| `GET /api/dashboard/summary` | `GET /api-dashboard/summary` |
| `GET /api/dashboard/ventas-dia` | `GET /api-dashboard/ventas-dia` |
| `GET /api/dashboard/ventas-mes` | `GET /api-dashboard/ventas-mes` |
| `GET /api/dashboard/carros-mas-avaluos` | `GET /api-dashboard/carros-mas-avaluos` |
| `GET /certificates/appraisal/{id}` | `GET /certificates-appraisal/{id}` |

Si quieres mantener las URLs originales con `/api/...`, hay dos opciones:
1. Crear una única función `api` que enrute internamente (menos modular).
2. Hacer un buscar-y-reemplazar en el frontend reemplazando los prefijos.

La opción 2 está más alineada con la arquitectura "una función = un recurso".

## 6. Notas técnicas

- **bcrypt**: se usa `npm:bcryptjs@2.4.3`. Los hashes `$2b$...` generados por
  Python (`passlib`/`bcrypt`) verifican correctamente con `bcryptjs`.
- **JWT**: `djwt@v3.0.2` con HS256 — mismo algoritmo y formato que python-jose.
  Tokens emitidos antes de la migración siguen siendo válidos siempre que el
  `JWT_SECRET` no cambie.
- **CORS**: `_shared/cors.ts` responde `*` a todas las origins. Si quieres
  restringirlo a Vercel, cambia `Access-Control-Allow-Origin`.
- **Certificado PDF**: la versión actual devuelve HTML imprimible. El navegador
  puede convertir a PDF (Ctrl/Cmd+P → Save as PDF). Si necesitas PDF real,
  añadir una llamada a un servicio externo o usar `pdf-lib` vía `npm:`.
- **`appraisal_deductions`**: el DDL no declara `ON DELETE CASCADE`, así que
  `api-appraisals` borra manualmente las deducciones antes de eliminar el avalúo.

## 7. Pasos sugeridos para la migración en producción

1. Hacer merge de este código a `main` → el workflow despliega las funciones.
2. Configurar los secrets de Supabase (paso 2) — sin ellos las funciones fallan.
3. Probar cada endpoint con `curl` o Postman antes de cambiar el frontend.
4. Actualizar `src/lib/constants.js` y los paths en el frontend; redeploy en Vercel.
5. Vigilar los logs en Supabase Dashboard → Edge Functions → Logs durante 24-48h.
6. Apagar/eliminar la app en Fly.io.
