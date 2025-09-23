export type UIState = Record<string, unknown>

export async function loadUiState(): Promise<UIState> {
  const resp = await fetch('/state/ui')
  if (!resp.ok) return {}
  const body = await resp.json()
  return body || {}
}

export async function patchUiState(patch: UIState): Promise<UIState> {
  const current = await loadUiState()
  const next = { ...current, ...patch }
  await fetch('/state/ui', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(next),
  })
  return next
}
