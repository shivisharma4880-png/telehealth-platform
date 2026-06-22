/** Base URL of the Telehealth FastAPI (no `/api/v1` suffix). Default 8001 avoids clashing with other local apps on 8000. */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "APIError";
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/api/v1${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const err = await response.json();
      message = err.detail || message;
    } catch {}
    throw new APIError(response.status, message);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

export const api = {
  get: <T>(endpoint: string, token?: string | null) =>
    request<T>(endpoint, { method: "GET" }, token),

  post: <T>(endpoint: string, data?: unknown, token?: string | null) =>
    request<T>(endpoint, { method: "POST", body: data ? JSON.stringify(data) : undefined }, token),

  put: <T>(endpoint: string, data: unknown, token?: string | null) =>
    request<T>(endpoint, { method: "PUT", body: JSON.stringify(data) }, token),

  patch: <T>(endpoint: string, data: unknown, token?: string | null) =>
    request<T>(endpoint, { method: "PATCH", body: JSON.stringify(data) }, token),

  delete: <T>(endpoint: string, token?: string | null) =>
    request<T>(endpoint, { method: "DELETE" }, token),

  uploadFile: async <T>(endpoint: string, formData: FormData, token?: string | null): Promise<T> => {
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(`${API_BASE_URL}/api/v1${endpoint}`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      let message = `HTTP ${response.status}`;
      try {
        const err = await response.json();
        message = err.detail || message;
      } catch {}
      throw new APIError(response.status, message);
    }

    return response.json();
  },
};

export { APIError };
