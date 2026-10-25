import createClient from "openapi-fetch";

import type { paths } from "./schema";

export const api = createClient<paths>({ baseUrl: "", credentials: "same-origin" });

export type FieldError = { field: string; message: string };

type ErrorBody = { error?: { code?: string; message?: string; details?: FieldError[] } };

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: FieldError[];

  constructor(status: number, code: string, message: string, details: FieldError[] = []) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/** Unwraps an openapi-fetch result, throwing ApiError with the server's message on failure. */
export async function call<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  let result: Awaited<typeof request>;
  try {
    result = await request;
  } catch {
    throw new ApiError(0, "NETWORK", "Could not reach the server. Check your connection.");
  }
  const { data, error, response } = result;
  if (!response.ok || error !== undefined) {
    const body = (error ?? {}) as ErrorBody;
    // A 5xx without our JSON error body means the API itself is down or unreachable.
    const fallback =
      response.status >= 500
        ? "The server is not responding right now. Please try again in a moment."
        : "Something went wrong. Please try again.";
    throw new ApiError(
      response.status,
      body.error?.code ?? "UNKNOWN",
      body.error?.message ?? fallback,
      body.error?.details ?? [],
    );
  }
  return data as T;
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}
