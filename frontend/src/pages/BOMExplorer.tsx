import React from 'react'
import PriceSparkline from '../components/PriceSparkline'

type Product = { type_id: number; name: string }
type TreeNode = { type_id: number; product_id: number; activity: string; materials: { type_id: number; qty: number }[]; children: TreeNode[] }

export default function BOMExplorer() {
  const [q, setQ] = React.useState('frigate')
  const [results, setResults] = React.useState<Product[]>([])
  const [selected, setSelected] = React.useState<Product | null>(null)
  const [tree, setTree] = React.useState<TreeNode | null>(null)
  const [cost, setCost] = React.useState<{ total_cost: number; lines: { type_id: number; qty: number; cost: number }[] } | null>(null)

  const search = async () => {
    const r = await fetch(`/bom/search?q=${encodeURIComponent(q)}`)
    if (r.ok) setResults((await r.json()).results)
  }
  const loadTree = async (p: Product) => {
    setSelected(p)
    const r = await fetch(`/bom/tree?product_id=${p.type_id}`)
    if (r.ok) setTree(await r.json())
    const c = await fetch(`/bom/cost`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ product_id: p.type_id, region_id: 10000002, runs: 1, me_bonus: 0.02 }) })
    if (c.ok) setCost(await c.json())
  }

  React.useEffect(() => { search() }, [])

  const renderTree = (n: TreeNode, depth = 0): JSX.Element => (
    <div key={`${n.product_id}-${depth}`} style={{ marginLeft: depth * 12 }}>
      <div>Product {n.product_id} ({n.activity})</div>
      {n.materials.map(m => <div key={`${n.product_id}-${m.type_id}`} style={{ marginLeft: 12 }}>• {m.type_id} × {m.qty}</div>)}
      {n.children?.map(c => renderTree(c, depth + 1))}
    </div>
  )

  return (
    <div className="card">
      <h3>BOM Explorer</h3>
      <div style={{ display: 'flex', gap: 8 }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search (e.g., frigate)" />
        <button className="btn" onClick={search}>Search</button>
      </div>
      <div style={{ marginTop: 8 }}>
        {results.slice(0, 10).map(r => (
          <button key={r.type_id} className="btn" onClick={() => loadTree(r)} style={{ marginRight: 6 }}>{r.name}</button>
        ))}
      </div>
      {selected && (
        <div style={{ marginTop: 12 }}>
          Selected: {selected.name}
          <div style={{ marginTop: 8 }}>
            <PriceSparkline typeId={selected.type_id} regionId={10000002} />
          </div>
        </div>
      )}
      {tree && <div style={{ marginTop: 12 }}>{renderTree(tree)}</div>}
      {cost && (
        <div className="card" style={{ marginTop: 12 }}>
          <div>Total Cost: {Math.round(cost.total_cost).toLocaleString()} ISK</div>
        </div>
      )}
    </div>
  )
}
