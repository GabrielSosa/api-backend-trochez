// Routes (all require Bearer token):
//   GET    /api-users                  -> list users
//   GET    /api-users/{id}             -> get user
//   PUT    /api-users/{id}             -> update user
//   DELETE /api-users/{id}             -> delete user

import { errorResponse, handlePreflight, jsonResponse, withErrorBoundary } from "../_shared/cors.ts";
import { getSupabase } from "../_shared/db.ts";
import { hashPassword } from "../_shared/hash.ts";
import { isHttpError, requireUser } from "../_shared/auth.ts";

function extractId(pathname: string): number | null {
  // Edge Function URL: /api-users or /api-users/{id}
  const parts = pathname.split("/").filter(Boolean);
  const idx = parts.findIndex((p) => p === "api-users");
  if (idx === -1 || idx === parts.length - 1) return null;
  const raw = parts[idx + 1];
  const n = Number(raw);
  return Number.isInteger(n) ? n : null;
}

Deno.serve(withErrorBoundary(async (req: Request) => {
  const preflight = handlePreflight(req);
  if (preflight) return preflight;

  try {
    await requireUser(req);
  } catch (e) {
    if (isHttpError(e)) return errorResponse(e.message, e.status);
    throw e;
  }

  const url = new URL(req.url);
  const id = extractId(url.pathname);
  const supabase = getSupabase();

  if (req.method === "GET" && id === null) {
    const { data, error } = await supabase
      .from("users")
      .select("user_id, name, email, user_type_id")
      .order("user_id", { ascending: true });
    if (error) return errorResponse(error.message, 500);
    return jsonResponse(data ?? []);
  }

  if (req.method === "GET" && id !== null) {
    const { data, error } = await supabase
      .from("users")
      .select("user_id, name, email, user_type_id")
      .eq("user_id", id)
      .maybeSingle();
    if (error) return errorResponse(error.message, 500);
    if (!data) return errorResponse("User not found", 404);
    return jsonResponse(data);
  }

  if (req.method === "PUT" && id !== null) {
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

    const update: Record<string, unknown> = {};
    if (typeof body.name === "string") update.name = body.name.trim();
    if (typeof body.email === "string") update.email = body.email.trim().toLowerCase();
    if (body.user_type_id !== undefined) update.user_type_id = body.user_type_id;
    if (typeof body.password === "string" && body.password.length > 0) {
      update.password = await hashPassword(body.password);
    }
    if (Object.keys(update).length === 0) {
      return errorResponse("No fields to update", 400);
    }

    const { data, error } = await supabase
      .from("users")
      .update(update)
      .eq("user_id", id)
      .select("user_id, name, email, user_type_id")
      .maybeSingle();
    if (error) return errorResponse(error.message, 500);
    if (!data) return errorResponse("User not found", 404);
    return jsonResponse(data);
  }

  if (req.method === "DELETE" && id !== null) {
    const { error } = await supabase.from("users").delete().eq("user_id", id);
    if (error) return errorResponse(error.message, 500);
    return jsonResponse({ detail: "User deleted" });
  }

  return errorResponse("Not found", 404);
}));
