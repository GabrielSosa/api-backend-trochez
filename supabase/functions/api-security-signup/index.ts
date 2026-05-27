// POST /functions/v1/api-security-signup
// Body: { name, email, password, user_type_id? }
// Auth: required

import { errorResponse, handlePreflight, jsonResponse } from "../_shared/cors.ts";
import { getSupabase } from "../_shared/db.ts";
import { hashPassword } from "../_shared/hash.ts";
import { isHttpError, requireUser } from "../_shared/auth.ts";

Deno.serve(async (req: Request) => {
  const preflight = handlePreflight(req);
  if (preflight) return preflight;

  if (req.method !== "POST") {
    return errorResponse("Method not allowed", 405);
  }

  try {
    await requireUser(req);
  } catch (e) {
    if (isHttpError(e)) return errorResponse(e.message, e.status);
    throw e;
  }

  let body: {
    name?: string;
    email?: string;
    password?: string;
    user_type_id?: number | null;
  };
  try {
    body = await req.json();
  } catch (_) {
    return errorResponse("Invalid JSON body", 400);
  }

  const name = body.name?.trim();
  const email = body.email?.trim().toLowerCase();
  const password = body.password;
  const userTypeId = body.user_type_id ?? null;

  if (!name || !email || !password) {
    return errorResponse("name, email and password are required", 400);
  }

  const supabase = getSupabase();

  const { data: existing } = await supabase
    .from("users")
    .select("user_id")
    .eq("email", email)
    .maybeSingle();
  if (existing) return errorResponse("Email already registered", 400);

  const hashed = await hashPassword(password);
  const { data: created, error } = await supabase
    .from("users")
    .insert({
      name,
      email,
      password: hashed,
      user_type_id: userTypeId,
    })
    .select("user_id, name, email, user_type_id")
    .single();

  if (error || !created) {
    console.error("signup insert error", error);
    return errorResponse("Could not create user", 500);
  }

  return jsonResponse(created, 201);
});
