import React from 'react'

type System = { system_id: number; name: string; indices: Record<string, number> }
type StructureCfg = { type: string; role: string; rigs: number[] }
type FacilitiesState = { systems: { system_id: number; name: string; structures: StructureCfg[] }[] }

export default function Systems() {
  const [items, setItems] = React.useState<System[]>([])
  const [expanded, setExpanded] = React.useState<Record<number, boolean>>({})
  const [facilities, setFacilities] = React.useState<FacilitiesState>({ systems: [] })
  const [search, setSearch] = React.useState<string>('')
  const [suggestions, setSuggestions] = React.useState<System[]>([])
  const [showSuggestions, setShowSuggestions] = React.useState<boolean>(false)
  const [rigs, setRigs] = React.useState<Record<string, { rig_id: number; name: string }[]>>({})

  React.useEffect(() => {
    fetch('/systems').then(r => r.ok ? r.json() : Promise.reject()).then(d => setItems(d.items || [])).catch(() => setItems([]))
    fetch('/state/ui').then(r => r.ok ? r.json() : Promise.reject()).then(s => setFacilities(s.facilities || { systems: [] })).catch(() => setFacilities({ systems: [] }))
  }, [])

  const persist = (next: FacilitiesState) => {
    setFacilities(next)
    fetch('/state/ui', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ facilities: next }) })
  }

  const addSystem = (sys: System) => {
    if (facilities.systems.find(s => s.system_id === sys.system_id)) return
    const next = { systems: [...facilities.systems, { system_id: sys.system_id, name: sys.name, structures: [] }] }
    persist(next)
    setShowSuggestions(false)
    setSearch('')
  }

  const addStructure = (system_id: number, cfg: StructureCfg) => {
    const next = { systems: facilities.systems.map(s => s.system_id === system_id ? { ...s, structures: [...s.structures, cfg] } : s) }
    persist(next)
  }

  const loadRigs = async (role: string) => {
    if (rigs[role]) return
    const r = await fetch(`/structures/rigs?activity=${encodeURIComponent(role)}`)
    if (r.ok) {
      const data = await r.json()
      setRigs({ ...rigs, [role]: data.rigs.map((x: any) => ({ rig_id: x.rig_id, name: x.name })) })
    }
  }

  return (
    <div className="card">
      <h3>Production Facilities</h3>
      <div style={{ position: 'relative' }}>
        <input
          placeholder="Search systems (e.g., Jita)"
          value={search}
          onChange={e => { setSearch(e.target.value); setShowSuggestions(true) }}
          onFocus={() => search && setShowSuggestions(true)}
          style={{ width: '100%', padding: 8, borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--fg)' }}
        />
        {showSuggestions && search && (
          <Suggestions
            query={search}
            onPick={(sys) => addSystem(sys)}
            onClose={() => setShowSuggestions(false)}
          />
        )}
      </div>
      <div style={{ marginTop: 8 }}>
        {items.map(s => (
          <div key={s.system_id} style={{ marginBottom: 8 }}>
            <div className="card" style={{ cursor: 'pointer' }} onClick={() => setExpanded({ ...expanded, [s.system_id]: !expanded[s.system_id] })}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <div>{s.name}</div>
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

function Suggestions({ query, onPick, onClose }: { query: string; onPick: (sys: System) => void; onClose: () => void }) {
  const [items, setItems] = React.useState<System[]>([])
  const [loading, setLoading] = React.useState(false)
  const [timer, setTimer] = React.useState<number | undefined>(undefined)

  React.useEffect(() => {
    if (timer) clearTimeout(timer)
    const id = window.setTimeout(async () => {
      setLoading(true)
      try {
        const r = await fetch(`/systems?q=${encodeURIComponent(query)}&limit=10`)
        if (r.ok) {
          const d = await r.json()
          setItems(d.items || [])
        }
      } finally {
        setLoading(false)
      }
    }, 250)
    setTimer(id)
    return () => clearTimeout(id)
  }, [query])

  return (
    <div className="card" style={{ position: 'absolute', top: '110%', left: 0, right: 0, zIndex: 5 }}>
      {loading && <div style={{ opacity: 0.7 }}>Searching…</div>}
      {!loading && !items.length && <div style={{ opacity: 0.7 }}>No results</div>}
      {items.map(s => (
        <div key={s.system_id} style={{ padding: '6px 4px', cursor: 'pointer' }} onClick={() => { onPick(s); onClose() }}>
          {s.name} <span style={{ opacity: 0.6 }}>#{s.system_id}</span>
        </div>
      ))}
    </div>
  )
}
