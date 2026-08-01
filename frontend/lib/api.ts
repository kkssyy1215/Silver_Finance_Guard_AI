const CONFIGURED_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");

function apiUrl(path: string): string {
  if (CONFIGURED_API_BASE_URL) return `${CONFIGURED_API_BASE_URL}${path}`;
  if (process.env.NODE_ENV === "development") return `http://127.0.0.1:8000${path}`;
  if (typeof window !== "undefined") return `${window.location.origin}${path}`;
  return `http://127.0.0.1:8000${path}`;
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };
    return data.detail ?? `요청에 실패했습니다. (${response.status})`;
  } catch {
    return `요청에 실패했습니다. (${response.status})`;
  }
}

export async function getJson<T>(path: string, query?: Record<string, string | number>): Promise<T> {
  const url = new URL(apiUrl(path));
  Object.entries(query ?? {}).forEach(([key, value]) => url.searchParams.set(key, String(value)));
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(await parseError(response));
  return (await response.json()) as T;
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return (await response.json()) as T;
}

export async function postFile<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(apiUrl(path), { method: "POST", body: formData });
  if (!response.ok) throw new Error(await parseError(response));
  return (await response.json()) as T;
}
