// JWT helpers — pure Web Crypto API implementation (no external dependencies).
// Uses HS256 with the JWT_SECRET configured as a Supabase secret.

import { getSupabase } from "./db.ts";

const ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24; // 24h

// ── Base64URL helpers ──────────────────────────────────────────────────────────

function base64urlEncode(data: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < data.length; i++) binary += String.fromCharCode(data[i]);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

function base64urlDecode(str: string): Uint8Array {
  const padded = str.replace(/-/g, "+").replace(/_/g, "/");
  const padding = (4 - (padded.length % 4)) % 4;
  const binary = atob(padded + "=".repeat(padding));
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

// ── Key helper ─────────────────────────────────────────────────────────────────

async function getKey(usage: "sign" | "verify"): Promise<CryptoKey> {
  const secret = Deno.env.get("JWT_SECRET");
  if (!secret) throw new Error("JWT_SECRET is not configured");
  return await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    [usage],
  );
}

// ── Create token ───────────────────────────────────────────────────────────────

export async function createAccessToken(
  payload: { sub: string; user_id: number; user_type_id: number | null },
): Promise<string> {
  const header = base64urlEncode(
    new TextEncoder().encode(JSON.stringify({ alg: "HS256", typ: "JWT" })),
  );
  const exp = Math.floor(Date.now() / 1000) + ACCESS_TOKEN_EXPIRE_MINUTES * 60;
  const body = base64urlEncode(
    new TextEncoder().encode(JSON.stringify({ ...payload, exp })),
  );
  const signing = header + "." + body;
  const key = await getKey("sign");
  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(signing),
  );
  return signing + "." + base64urlEncode(new Uint8Array(sig));
}

// ── Verify token ───────────────────────────────────────────────────────────────

export interface TokenUser {
  user_id: number;
  email: string;
  user_type_id: number | null;
}

export async function requireUser(req: Request): Promise<TokenUser> {
  const authHeader =
    req.headers.get("authorization") ?? req.headers.get("Authorization");
  if (!authHeader || !authHeader.toLowerCase().startsWith("bearer ")) {
    throw httpError("Not authenticated", 401);
  }
  const token = authHeader.slice(7).trim();

  const parts = token.split(".");
  if (parts.length !== 3) throw httpError("Could not validate credentials", 401);

  const [header, body, sigB64] = parts;
  const signing = header + "." + body;

  // Verify signature
  let valid = false;
  try {
    const key = await getKey("verify");
    const sigBytes = base64urlDecode(sigB64);
    valid = await crypto.subtle.verify(
      "HMAC",
      key,
      sigBytes,
      new TextEncoder().encode(signing),
    );
  } catch (_) {
    throw httpError("Could not validate credentials", 401);
  }
  if (!valid) throw httpError("Could not validate credentials", 401);

  // Decode payload
  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(new TextDecoder().decode(base64urlDecode(body)));
  } catch (_) {
    throw httpError("Could not validate credentials", 401);
  }

  // Check expiry
  const exp = payload.exp as number | undefined;
  if (exp && Math.floor(Date.now() / 1000) > exp) {
    throw httpError("Token expired", 401);
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

// ── Error helpers ──────────────────────────────────────────────────────────────

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
