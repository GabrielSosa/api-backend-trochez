// JWT helpers — drop-in replacement for python-jose HS256 tokens used by the
// FastAPI backend. The same JWT_SECRET must be configured as a Supabase secret
// so previously issued tokens keep validating.

import {
  create,
  verify,
  getNumericDate,
  Payload,
} from "https://deno.land/x/djwt@v3.0.2/mod.ts";
import { getSupabase } from "./db.ts";

const ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24; // 24h, same default as the FastAPI app

async function getKey(): Promise<CryptoKey> {
  const secret = Deno.env.get("JWT_SECRET");
  if (!secret) throw new Error("JWT_SECRET is not configured");

  return await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
}

export interface TokenUser {
  user_id: number;
  email: string;
  user_type_id: number | null;
}

export async function createAccessToken(
  payload: { sub: string; user_id: number; user_type_id: number | null },
): Promise<string> {
  const key = await getKey();
  const jwt = await create(
    { alg: "HS256", typ: "JWT" },
    {
      ...payload,
      exp: getNumericDate(ACCESS_TOKEN_EXPIRE_MINUTES * 60),
    } as Payload,
    key,
  );
  return jwt;
}

/**
 * Verify the Authorization header and return the user record from the DB.
 * Throws an Error with `.status` set when authentication fails — callers can
 * convert that into a JSON error response.
 */
export async function requireUser(req: Request): Promise<TokenUser> {
  const authHeader = req.headers.get("authorization") ?? req.headers.get("Authorization");
  if (!authHeader || !authHeader.toLowerCase().startsWith("bearer ")) {
    throw httpError("Not authenticated", 401);
  }
  const token = authHeader.slice(7).trim();

  let payload: Payload;
  try {
    const key = await getKey();
    payload = await verify(token, key);
  } catch (_) {
    throw httpError("Could not validate credentials", 401);
  }

  const email = (payload.sub as string | undefined) ?? null;
  if (!email) throw httpError("Could not validate credentials", 401);

  const supabase = getSupabase();
  const { data, error } = await supabase
    .from("users")
    .select("user_id, email, user_type_id")
    .eq("email", email)
    .maybeSingle();

  if (error || !data) throw httpError("User not found", 401);

  return {
    user_id: data.user_id,
    email: data.email,
    user_type_id: data.user_type_id,
  };
}

export interface HttpError extends Error {
  status: number;
}

export function httpError(message: string, status: number): HttpError {
  const err = new Error(message) as HttpError;
  err.status = status;
  return err;
}

export function isHttpError(e: unknown): e is HttpError {
  return e instanceof Error && typeof (e as HttpError).status === "number";
}
