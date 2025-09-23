import React from 'react'
import PriceSparkline from '../components/PriceSparkline'

type Product = { type_id: number; name: string }
type BasketItem = { product: Product; qty: number; cost?: number; expanded?: boolean; tree?: TreeNode }
type TreeNode = { type_id: number; product_id: number; activity: string; materials: { type_id: number; qty: number }[]; children: TreeNode[] }

export default function ShipBasket() {
  const [q, setQ] = React.useState('')
  const [suggestions, setSuggestions] = React.useState<Product[]>([])
  const [basket, setBasket] = React.useState<BasketItem[]>([])

  React.useEffect(() => {
    fetch('/state/ui').then(r => r.ok ? r.json() : Promise.reject()).then(s => setBasket(s.basket || [])).catch(() => setBasket([]))
  }, [])

  const persist = (next: BasketItem[]) => {
    setBasket(next)
    fetch('/state/ui', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ basket: next }) })
  }

  React.useEffect(() => {
    if (!q) { setSuggestions([]); return }
    const id = window.setTimeout(async () => {
      const r = await fetch(`/bom/search?q=${encodeURIComponent(q)}&limit=10`)
      if (r.ok) setSuggestions((await r.json()).results || [])
    }, 250)
    return () => clearTimeout(id)
  }, [q])

  const add = (p: Product) => {
    if (basket.find(b => b.product.type_id === p.type_id)) return
    const next = [...basket, { product: p, qty: 1, expanded: false }]
    persist(next)
    setQ(''); setSuggestions([])
    priceAndCost(p, 1)
    loadTree(p)
  }

  const updateQty = (idx: number, qty: number) => {
    const next = basket.map((b, i) => i === idx ? { ...b, qty } : b)
    persist(next)
    priceAndCost(next[idx].product, qty)
  }

  const priceAndCost = async (p: Product, runs: number) => {
    await fetch(`/bom/cost`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ product_id: p.type_id, region_id: 10000002, runs, me_bonus: 0.02 }) })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(c => {
        const next = basket.map(b => b.product.type_id === p.type_id ? { ...b, cost: c.total_cost } : b)
        setBasket(next)
      }).catch(() => {})
  }

  const loadTree = async (p: Product) => {
    const r = await fetch(`/bom/tree?product_id=${p.type_id}`)
    if (r.ok) {
      const t = await r.json()
      setBasket(basket.map(b => b.product.type_id === p.type_id ? { ...b, tree: t } : b))
    }
  }

  const total = Math.round(basket.reduce((s, b) => s + (b.cost || 0), 0))

  return (
    <div className="card">
      <h3>Ship Basket</h3>
      <div style={{ position: 'relative', marginBottom: 8 }}>
        <input placeholder="Search T2 frigates/cruisers" value={q} onChange={(e) => setQ(e.target.value)} />
        {!!suggestions.length && (
          <div className="card" style={{ position: 'absolute', zIndex: 5, left: 0, right: 0 }}>
            {suggestions.map(s => <div key={s.type_id} style={{ cursor: 'pointer', padding: 6 }} onClick={() => add(s)}>{s.name}</div>)}
          </div>
        )}
      </div>
      <div className="card" style={{ marginBottom: 8 }}>Grand Total Cost: {total.toLocaleString()} ISK</div>
      {basket.map((b, i) => (
        <div key={b.product.type_id} className="card" style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div>{b.product.name}</div>
            <div>
              Qty: <input type="number" min={1} value={b.qty} onChange={(e) => updateQty(i, Number(e.target.value || 1))} />
              <button className="btn" style={{ marginLeft: 8 }} onClick={() => setBasket(basket.map((it, idx) => idx===i ? { ...it, expanded: !it.expanded } : it))}>{b.expanded ? 'Collapse' : 'Expand'}</button>
            </div>
          </div>
          <div style={{ marginTop: 6 }}>
            <PriceSparkline typeId={b.product.type_id} regionId={10000002} />
          </div>
          <div style={{ marginTop: 6 }}>Cost: {Math.round(b.cost || 0).toLocaleString()} ISK</div>
          {b.expanded && b.tree && (
            <div style={{ marginTop: 8 }}>{renderTree(b.tree)}</div>
          )}
        </div>
      ))}
    </div>
  )
}

function renderTree(n: TreeNode, depth: number = 0): JSX.Element {
  return (
    <div key={`${n.product_id}-${depth}`} style={{ marginLeft: depth * 12 }}>
      <div>Product {n.product_id} ({n.activity})</div>
      {n.materials.map(m => <div key={`${n.product_id}-${m.type_id}`} style={{ marginLeft: 12 }}>• {m.type_id} × {m.qty}</div>)}
      {n.children?.map(c => renderTree(c, depth + 1))}
    </div>
  )
}
