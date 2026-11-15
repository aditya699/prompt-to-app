// Leave VITE_API_URL empty when the client is served from the same origin as the API
// (the VM setup in deploy/). Locally it points at the FastAPI dev server.
export const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

/** An error response from the API, carrying the server's `{error: {code, message}}`. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const body = await response.json();
    if (body?.error) return new ApiError(response.status, body.error.code, body.error.message);
    if (Array.isArray(body?.detail)) {
      const first = body.detail[0];
      return new ApiError(response.status, "validation_error", first?.msg ?? "Invalid request");
    }
  } catch {
    // fall through to a generic error
  }
  return new ApiError(response.status, "http_error", `Request failed with ${response.status}`);
}

/** JSON request helper. Throws `ApiError` on a non-2xx response. */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/**
 * Read a Server-Sent Events stream with `fetch`, calling `onEvent` for each
 * `data:` payload. Resolves when the server ends the stream.
 */
export async function readSSE<T>(
  path: string,
  onEvent: (event: T) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Accept: "text/event-stream" },
    signal,
  });
  if (!response.ok || !response.body) throw await toApiError(response);

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const data = block
        .split("\n")
        .filter((line) => line.startsWith("data: "))
        .map((line) => line.slice(6))
        .join("\n");
      if (data) onEvent(JSON.parse(data) as T);
      boundary = buffer.indexOf("\n\n");
    }
  }
}
