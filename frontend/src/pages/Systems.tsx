import React from 'react'

type System = {
  system_id: number
  name: string
  indices: Record<string, number>
  region_id?: number | null
  region_name?: string | null
  constellation_id?: number | null
  constellation_name?: string | null
}
type StructureCfg = { type: string; role: string; rigs: number[] }
type FacilitiesState = { systems: { system_id: number; name: string; structures: StructureCfg[] }[] }

export default function Systems() {
  const [items, setItems] = React.useState<System[]>([])
  const [expanded, setExpanded] = React.useState<Record<number, boolean>>({})
  const [facilities, setFacilities] = React.useState<FacilitiesState>({ systems: [] })
  const [search, setSearch] = React.useState<string>('')
  const [regionFilter, setRegionFilter] = React.useState<string>('')
  const [constellationFilter, setConstellationFilter] = React.useState<string>('')
  const [suggestions, setSuggestions] = React.useState<System[]>([])
  const [suggestCursor, setSuggestCursor] = React.useState<number | null>(null)
  const [highlight, setHighlight] = React.useState<number>(-1)
  const [suggestLoading, setSuggestLoading] = React.useState<boolean>(false)
  const [rigs, setRigs] = React.useState<Record<string, { rig_id: number; name: string }[]>>({})

  React.useEffect(() => {
    fetch('/state/ui')
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then(state => setFacilities(state.facilities || { systems: [] }))
      .catch(() => setFacilities({ systems: [] }))
  }, [])

  const loadSystems = React.useCallback(() => {
    const params = new URLSearchParams({ limit: '50' })
    if (regionFilter) params.set('region_id', regionFilter)
    if (constellationFilter) params.set('constellation_id', constellationFilter)
    fetch(`/systems?${params.toString()}`)
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then(data => setItems(data.items || []))
      .catch(() => setItems([]))
  }, [regionFilter, constellationFilter])

  React.useEffect(() => { loadSystems() }, [loadSystems])

  const persist = (next: FacilitiesState) => {
    setFacilities(next)
    fetch('/state/ui', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ facilities: next }) })
  }

  const addSystem = (sys: System) => {
    if (facilities.systems.find(s => s.system_id === sys.system_id)) return
    const next = { systems: [...facilities.systems, { system_id: sys.system_id, name: sys.name, structures: [] }] }
    persist(next)
    setSearch('')
    setSuggestions([])
    setSuggestCursor(null)
    setHighlight(-1)
  }

  const addStructure = (system_id: number, cfg: StructureCfg) => {
    const next = { systems: facilities.systems.map(s => s.system_id === system_id ? { ...s, structures: [...s.structures, cfg] } : s) }
    persist(next)
  }

  const loadRigs = async (role: string) => {
    if (rigs[role]) return
    const response = await fetch(`/structures/rigs?activity=${encodeURIComponent(role)}`)
    if (response.ok) {
      const data = await response.json()
      setRigs({ ...rigs, [role]: data.rigs.map((x: any) => ({ rig_id: x.rig_id, name: x.name })) })
    }
  }

  const fetchSuggestions = React.useCallback(async (append: boolean, cursor?: number | null) => {
    if (!search) { setSuggestions([]); setSuggestCursor(null); setHighlight(-1); return }
    setSuggestLoading(true)
    const params = new URLSearchParams({ q: search, limit: '10' })
    if (regionFilter) params.set('region_id', regionFilter)
    if (constellationFilter) params.set('constellation_id', constellationFilter)
    if (cursor) params.set('cursor', String(cursor))
    try {
      const res = await fetch(`/systems?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        const newItems: System[] = data.items || []
        setSuggestions(prev => append ? [...prev, ...newItems] : newItems)
        setSuggestCursor(data.next_cursor ?? null)
        setHighlight(prev => append ? prev : (newItems.length ? 0 : -1))
      }
    } finally {
      setSuggestLoading(false)
    }
  }, [search, regionFilter, constellationFilter])

  React.useEffect(() => {
    if (!search) { setSuggestions([]); setSuggestCursor(null); setHighlight(-1); return }
    const id = window.setTimeout(() => { fetchSuggestions(false) }, 200)
    return () => window.clearTimeout(id)
  }, [search, regionFilter, constellationFilter, fetchSuggestions])

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (!suggestions.length) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setHighlight(prev => {
        const next = prev + 1
        if (next >= suggestions.length) {
          if (suggestCursor) fetchSuggestions(true, suggestCursor)
          return suggestions.length - 1
        }
        return next
      })
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setHighlight(prev => Math.max(0, prev - 1))
    } else if (event.key === 'Enter') {
      event.preventDefault()
      if (highlight >= 0 && suggestions[highlight]) addSystem(suggestions[highlight])
    } else if (event.key === 'Escape') {
      setSuggestions([])
      setHighlight(-1)
    }
  }

  return (
    <div className="card">
      <h3>Production Facilities</h3>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <label style={{ flex: 1 }}>Region ID
          <input type="number" value={regionFilter} onChange={e => setRegionFilter(e.target.value)} style={{ width: '100%', marginTop: 4 }} />
        </label>
        <label style={{ flex: 1 }}>Constellation ID
          <input type="number" value={constellationFilter} onChange={e => setConstellationFilter(e.target.value)} style={{ width: '100%', marginTop: 4 }} />
        </label>
      </div>
      <div style={{ position: 'relative' }}>
        <input
          placeholder="Search systems (e.g., Jita)"
          value={search}
          onChange={e => setSearch(e.target.value)}
          onKeyDown={onKeyDown}
          style={{ width: '100%', padding: 8, borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--fg)' }}
        />
        {!!suggestions.length && (
          <div className="card" style={{ position: 'absolute', top: '110%', left: 0, right: 0, zIndex: 5, padding: 8 }}>
            {suggestions.map((sys, idx) => (
              <div
                key={sys.system_id}
                className={idx === highlight ? 'system-suggestion active' : 'system-suggestion'}
                onMouseDown={() => addSystem(sys)}
              >
                <div>{sys.name}</div>
                <div className="system-suggestion__meta">#{sys.system_id} · {sys.region_name || sys.region_id || 'Region?'} · {sys.constellation_name || sys.constellation_id || 'Const?'}</div>
              </div>
            ))}
            {suggestCursor && (
              <button className="btn" style={{ marginTop: 6 }} onMouseDown={() => fetchSuggestions(true, suggestCursor)}>Load more</button>
            )}
            {suggestLoading && <div style={{ opacity: 0.7, marginTop: 4 }}>Searching…</div>}
          </div>
        )}
      </div>
      <div style={{ marginTop: 8 }}>
        {items.map(s => (
          <div key={s.system_id} style={{ marginBottom: 8 }}>
            <div className="card" style={{ cursor: 'pointer' }} onClick={() => setExpanded({ ...expanded, [s.system_id]: !expanded[s.system_id] })}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <div>
                  <div>{s.name}</div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>{s.region_name || s.region_id || '—'} · {s.constellation_name || s.constellation_id || '—'}</div>
                </div>
                <div style={{ opacity: 0.8 }}>
                  {Object.entries(s.indices || {}).map(([k, v]) => <span key={k} style={{ marginLeft: 8 }}>{k}: {(Number(v) * 100).toFixed(2)}%</span>)}
                </div>
              </div>
            </div>
            {expanded[s.system_id] && (
              <div className="card" style={{ marginTop: 6 }}>
                <AddStructureForm onAdd={(cfg) => addStructure(s.system_id, cfg)} loadRigs={loadRigs} rigs={rigs} />
                <div style={{ marginTop: 8 }}>
                  {(facilities.systems.find(ss => ss.system_id === s.system_id)?.structures || []).map((st, idx) => (
                    <div key={idx} style={{ opacity: 0.9 }}>• {st.type} — {st.role} — Rigs: {st.rigs.join(', ') || 'None'}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function AddStructureForm({ onAdd, loadRigs, rigs }: { onAdd: (cfg: StructureCfg) => void, loadRigs: (role: string) => void, rigs: Record<string, { rig_id: number; name: string }[]> }) {
  const [type, setType] = React.useState<string>('Raitaru')
  const [role, setRole] = React.useState<string>('Manufacturing')
  const [selectedRigs, setSelectedRigs] = React.useState<Record<number, boolean>>({})
  React.useEffect(() => { loadRigs(role) }, [role])
  const rigList = rigs[role] || []
  return (
    <div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <label>Structure:&nbsp;
          <select value={type} onChange={e => setType(e.target.value)}>
            {['Tatara', 'Athanor', 'Raitaru', 'Azbel', 'Sotiyo'].map(s => <option key={s}>{s}</option>)}
          </select>
        </label>
        <label>Role:&nbsp;
          <select value={role} onChange={e => setRole(e.target.value)}>
            {['Manufacturing', 'Reactions', 'Refining', 'Science'].map(r => <option key={r}>{r}</option>)}
          </select>
        </label>
        <button className="btn" onClick={() => onAdd({ type, role, rigs: Object.entries(selectedRigs).filter(([k,v]) => v).map(([k]) => Number(k)) })}>Add</button>
      </div>
      <div style={{ marginTop: 6 }}>
        {rigList.length ? rigList.map(r => (
          <label key={r.rig_id} style={{ marginRight: 12 }}>
            <input type="checkbox" checked={!!selectedRigs[r.rig_id]} onChange={(e) => setSelectedRigs({ ...selectedRigs, [r.rig_id]: e.target.checked })} /> {r.name}
          </label>
        )) : <div style={{ opacity: 0.6 }}>No rigs available for {role}</div>}
      </div>
    </div>
  )
}

