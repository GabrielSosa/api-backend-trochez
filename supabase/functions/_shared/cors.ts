// Shared CORS headers for all Edge Functions.
// Allows requests from the Vercel-hosted SvelteKit frontend (and any other origin).

export const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type, accept",
  "Access-Control-Max-Age": "86400",
};

export function handlePreflight(req: Request): Response | null {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  return null;
}

export function jsonResponse(
  body: unknown,
  status = 200,
  extraHeaders: Record<string, string> = {},
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...corsHeaders,
      "Content-Type": "application/json",
      ...extraHeaders,
    },
  });
}

export function errorResponse(message: string, status = 400): Response {
  return jsonResponse({ detail: message }, status);
}

/**
 * Wraps a Deno.serve handler so uncaught throws return a JSON 500 with the
 * actual message + stack instead of an opaque EDGE_FUNCTION_ERROR. Logs the
 * full error to console.error so it shows up in the Edge Function logs tab.
 */
export function withErrorBoundary(
  handler: (req: Request) => Promise<Response> | Response,
): (req: Request) => Promise<Response> {
  return async (req: Request) => {
    try {
      return await handler(req);
    } catch (e) {
      const err = e as Error;
      console.error("Unhandled error in edge function:", err?.stack ?? err);
      return jsonResponse(
        {
          detail: "Internal server error",
          error: err?.message ?? String(err),
          stack: err?.stack ?? null,
        },
        500,
      );
    }
  };
}
