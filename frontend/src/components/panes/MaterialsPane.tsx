import React from 'react'

type Item = { type_id: number; qty: number; avg_cost?: number }

const MaterialsPane: React.FC = () => {
  const [ownerScope, setOwnerScope] = React.useState('corp')
  const [onHand, setOnHand] = React.useState<Item[]>([])
  const [wip, setWip] = React.useState<Item[]>([])
  const [loading, setLoading] = React.useState(false)

  const load = React.useCallback(async () => {
    setLoading(true)
    try {
      const [handRes, wipRes] = await Promise.all([
        fetch(`/inventory/valuation?owner_scope=${encodeURIComponent(ownerScope)}`),
        fetch(`/inventory/wip?owner_scope=${encodeURIComponent(ownerScope)}`),
      ])
      const handData = handRes.ok ? await handRes.json() : null
      const wipData = wipRes.ok ? await wipRes.json() : null
      setOnHand(handData?.items || [])
      setWip(wipData?.items || [])
    } finally {
      setLoading(false)
    }
  }, [ownerScope])

  React.useEffect(() => { load() }, [load])

  return (
    <div className="pane-materials">
      <div className="pane-materials__controls">
        <label>
          Owner Scope
          <input value={ownerScope} onChange={(e) => setOwnerScope(e.target.value)} />
        </label>
        <button className="btn" onClick={load} disabled={loading}>Refresh</button>
      </div>
      {loading && <div style={{ opacity: 0.7 }}>Loading inventory…</div>}
      {!loading && (
        <div className="pane-materials__grid">
          <div>
            <h4>On-hand (Rolling Average)</h4>
            {onHand.length ? onHand.map(item => (
              <div key={item.type_id} className="pane-materials__row">
                <span>Type {item.type_id}</span>
                <span>{Number(item.qty).toLocaleString()} units @ {Number(item.avg_cost || 0).toFixed(2)} ISK</span>
              </div>
            )) : <div style={{ opacity: 0.7 }}>No inventory records.</div>}
          </div>
          <div>
            <h4>Work in Progress</h4>
            {wip.length ? wip.map(item => (
              <div key={item.type_id} className="pane-materials__row">
                <span>Type {item.type_id}</span>
                <span>{Number(item.qty).toLocaleString()} units</span>
              </div>
            )) : <div style={{ opacity: 0.7 }}>No active jobs.</div>}
          </div>
        </div>
      )}
    </div>
  )
}

export default MaterialsPane
