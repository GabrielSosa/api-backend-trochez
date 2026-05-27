// POST /functions/v1/api-security-signin
// Body: { email, password }
// Returns: { access_token, token_type, user: { user_id, name, email, user_type_id } }

import { errorResponse, handlePreflight, jsonResponse, withErrorBoundary } from "../_shared/cors.ts";
import { getSupabase } from "../_shared/db.ts";
import { verifyPassword } from "../_shared/hash.ts";
import { createAccessToken } from "../_shared/auth.ts";

Deno.serve(withErrorBoundary(async (req: Request) => {
  const preflight = handlePreflight(req);
  if (preflight) return preflight;

  if (req.method !== "POST") {
    return errorResponse("Method not allowed", 405);
  }

  let body: { email?: string; password?: string };
  try {
    body = await req.json();
  } catch (_) {
    return errorResponse("Invalid JSON body", 400);
  }

  const email = body.email?.trim().toLowerCase();
  const password = body.password;
  if (!email || !password) {
    return errorResponse("email and password are required", 400);
  }

  const supabase = getSupabase();
  const { data: user, error } = await supabase
    .from("users")
    .select("user_id, name, email, password, user_type_id")
    .eq("email", email)
    .maybeSingle();

  if (error) {
    console.error("signin db error", error);
    return errorResponse("Internal server error", 500);
  }
  if (!user) return errorResponse("Incorrect email or password", 401);

  const ok = await verifyPassword(password, user.password);
  if (!ok) return errorResponse("Incorrect email or password", 401);

  const accessToken = await createAccessToken({
    sub: user.email,
    user_id: user.user_id,
    user_type_id: user.user_type_id,
  });

  return jsonResponse({
    access_token: accessToken,
    token_type: "bearer",
    user: {
      user_id: user.user_id,
      name: user.name,
      email: user.email,
      user_type_id: user.user_type_id,
    },
  });
}));
