export async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return (await res.json()) as T
}

export async function postJSON<T>(path: string, body: unknown): Promise<T> {
  return getJSON<T>(path, { method: 'POST', body: JSON.stringify(body) })
}

