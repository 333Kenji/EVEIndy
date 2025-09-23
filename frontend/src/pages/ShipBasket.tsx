import React from 'react'
import PriceSparkline from '../components/PriceSparkline'

type Product = { type_id: number; name: string }
type TreeNode = { type_id: number; product_id: number; activity: string; materials: { type_id: number; qty: number }[]; children: TreeNode[] }
type QuoteMetrics = {
  bid: number
  ask: number
  mid: number
  spread: number
  bid_qty: number
  ask_qty: number
  depth_qty_1pct: number
  depth_qty_5pct: number
  ts: string
}
type BasketItem = {
  product: Product
  qty: number
  cost?: number
  saleGross?: number
  saleNet?: number
  profit?: number
  quote?: QuoteMetrics
  expanded?: boolean
  tree?: TreeNode
  loading?: boolean
}

type PlanSettings = {
  regionId: number
  meBonus: number
  brokerFee: number
  salesTax: number
}

const DEFAULT_SETTINGS: PlanSettings = {
  regionId: 10000002,
  meBonus: 0.02,
  brokerFee: 0.03,
  salesTax: 0.015,
}

const SEARCH_DELAY = 250

export default function ShipBasket() {
  const [search, setSearch] = React.useState('')
  const [suggestions, setSuggestions] = React.useState<Product[]>([])
  const [basket, setBasket] = React.useState<BasketItem[]>([])
  const [settings, setSettings] = React.useState<PlanSettings>(DEFAULT_SETTINGS)
  const searchTimer = React.useRef<number | null>(null)

  React.useEffect(() => {
    fetch('/state/ui')
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then((state) => {
        const saved = state.shipBasket || {}
        const savedBasket = saved.basket || state.basket || []
        setBasket(savedBasket)
        setSettings({ ...DEFAULT_SETTINGS, ...(saved.settings || {}) })
      })
      .catch(() => {
        setBasket([])
        setSettings(DEFAULT_SETTINGS)
      })
  }, [])

  const persist = React.useCallback((nextBasket: BasketItem[] = basket, nextSettings: PlanSettings = settings) => {
    fetch('/state/ui', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shipBasket: { basket: nextBasket, settings: nextSettings } }),
    }).catch(() => {})
  }, [basket, settings])

  React.useEffect(() => {
    if (!search) {
      setSuggestions([])
      return
    }
    if (searchTimer.current) window.clearTimeout(searchTimer.current)
    searchTimer.current = window.setTimeout(async () => {
      const res = await fetch(`/bom/search?q=${encodeURIComponent(search)}&limit=12`)
      if (res.ok) {
        const data = await res.json()
        setSuggestions(data.results || [])
      }
    }, SEARCH_DELAY)
    return () => {
      if (searchTimer.current) window.clearTimeout(searchTimer.current)
    }
  }, [search])

  const refreshMetrics = React.useCallback(async (product: Product, runs: number) => {
    const regionId = settings.regionId
    const meBonus = settings.meBonus
    try {
      const [costRes, quoteRes] = await Promise.all([
        fetch('/bom/cost', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ product_id: product.type_id, region_id: regionId, runs, me_bonus: meBonus }),
        }),
        fetch('/prices/quotes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ region_id: regionId, type_ids: [product.type_id] }),
        }),
      ])
      const costData = costRes.ok ? await costRes.json() : null
      const quoteData = quoteRes.ok ? await quoteRes.json() : null
      const quote = quoteData?.quotes?.[0]
      setBasket(prev => prev.map((item) => {
        if (item.product.type_id !== product.type_id) return item
        const totalCost = Number(costData?.total_cost || 0)
        const grossSale = quote ? Number(quote.ask) * runs : undefined
        const netSale = quote && grossSale !== undefined
          ? grossSale * (1 - settings.brokerFee - settings.salesTax)
          : undefined
        const profit = grossSale !== undefined && netSale !== undefined ? netSale - totalCost : undefined
        const metrics: QuoteMetrics | undefined = quote ? {
          bid: Number(quote.bid),
          ask: Number(quote.ask),
          mid: Number(quote.mid),
          spread: Number(quote.spread),
          bid_qty: Number(quote.bid_qty),
          ask_qty: Number(quote.ask_qty),
          depth_qty_1pct: Number(quote.depth_qty_1pct),
          depth_qty_5pct: Number(quote.depth_qty_5pct),
          ts: quote.ts,
        } : undefined
        return {
          ...item,
          cost: totalCost,
          saleGross: grossSale,
          saleNet: netSale,
          profit,
          quote: metrics,
          loading: false,
        }
      }))
    } catch (err) {
      setBasket(prev => prev.map((item) => (item.product.type_id === product.type_id ? { ...item, loading: false } : item)))
    }
  }, [settings])

  const addProduct = async (product: Product) => {
    if (basket.find(b => b.product.type_id === product.type_id)) return
    const next = [...basket, { product, qty: 1, expanded: false, loading: true }]
    setBasket(next)
    persist(next, settings)
    setSearch('')
    setSuggestions([])
    refreshMetrics(product, 1)
    loadTree(product)
  }

  const updateQty = (index: number, qty: number) => {
    const sanitized = Math.max(1, qty)
    setBasket(prev => prev.map((item, i) => (i === index ? { ...item, qty: sanitized, loading: true } : item)))
    const product = basket[index]?.product
    if (product) {
      refreshMetrics(product, sanitized)
    }
    const next = basket.map((item, i) => (i === index ? { ...item, qty: sanitized } : item))
    persist(next, settings)
  }

  const remove = (productId: number) => {
    const next = basket.filter(b => b.product.type_id !== productId)
    setBasket(next)
    persist(next, settings)
  }

  const toggleExpanded = (index: number) => {
    setBasket(prev => prev.map((item, i) => (i === index ? { ...item, expanded: !item.expanded } : item)))
  }

  const loadTree = async (product: Product) => {
    const res = await fetch(`/bom/tree?product_id=${product.type_id}`)
    if (res.ok) {
      const tree = await res.json()
      setBasket(prev => prev.map(item => (item.product.type_id === product.type_id ? { ...item, tree } : item)))
    }
  }

  const updateSettings = (partial: Partial<PlanSettings>) => {
    const next = { ...settings, ...partial }
    setSettings(next)
    persist(basket, next)
  }

  const basketSignature = React.useMemo(() => basket.map(item => `${item.product.type_id}:${item.qty}`).join('|'), [basket])

  React.useEffect(() => {
    if (!basket.length) return
    basket.forEach(item => {
      if (item.loading || item.cost === undefined) {
        refreshMetrics(item.product, item.qty)
      }
    })
  }, [refreshMetrics, basketSignature])

  const totals = basket.reduce((acc, item) => {
    acc.cost += item.cost || 0
    acc.sale += item.saleNet || 0
    acc.gross += item.saleGross || 0
    acc.profit += item.profit || 0
    return acc
  }, { cost: 0, sale: 0, gross: 0, profit: 0 })

  const profitMargin = totals.sale > 0 ? totals.profit / totals.sale : 0

  return (
    <div className="card ship-basket">
      <div className="ship-basket__header">
        <div>
          <h3>Ship Basket</h3>
          <p className="ship-basket__subtitle">Plan builds with live pricing, cost inputs, and deterministic profit math.</p>
        </div>
        <div className="ship-basket__summary">
          <div>
            <span className="ship-basket__summary-label">Net Sale</span>
            <span className="ship-basket__summary-value">{Math.round(totals.sale).toLocaleString()} ISK</span>
          </div>
          <div>
            <span className="ship-basket__summary-label">Total Cost</span>
            <span className="ship-basket__summary-value">{Math.round(totals.cost).toLocaleString()} ISK</span>
          </div>
          <div>
            <span className="ship-basket__summary-label">Profit</span>
            <span className="ship-basket__summary-value accent">{Math.round(totals.profit).toLocaleString()} ISK</span>
          </div>
          <div>
            <span className="ship-basket__summary-label">Margin</span>
            <span className="ship-basket__summary-value">{(profitMargin * 100).toFixed(1)}%</span>
          </div>
        </div>
      </div>

      <div className="ship-basket__controls card">
        <div className="ship-basket__control">
          <label>Market Region</label>
          <input type="number" value={settings.regionId} onChange={e => updateSettings({ regionId: Number(e.target.value || 0) })} />
        </div>
        <div className="ship-basket__control">
          <label>ME Bonus</label>
          <input type="range" min={0} max={0.1} step={0.01} value={settings.meBonus} onChange={e => updateSettings({ meBonus: Number(e.target.value) })} />
          <span className="ship-basket__control-note">{(settings.meBonus * 100).toFixed(0)}%</span>
        </div>
        <div className="ship-basket__control">
          <label>Broker Fee</label>
          <input type="number" step={0.001} value={settings.brokerFee} onChange={e => updateSettings({ brokerFee: Number(e.target.value || 0) })} />
        </div>
        <div className="ship-basket__control">
          <label>Sales Tax</label>
          <input type="number" step={0.001} value={settings.salesTax} onChange={e => updateSettings({ salesTax: Number(e.target.value || 0) })} />
        </div>
      </div>

      <div className="ship-basket__search">
        <input
          placeholder="Search T2 frigates/cruisers"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        {!!suggestions.length && (
          <div className="card ship-basket__suggestions">
            {suggestions.map(s => (
              <button key={s.type_id} className="ship-basket__suggestion" onClick={() => addProduct(s)}>
                <span>{s.name}</span>
                <span className="ship-basket__suggestion-meta">#{s.type_id}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="ship-basket__items">
        {basket.map((item, index) => (
          <article key={item.product.type_id} className="ship-card">
            <header className="ship-card__header">
              <div className="ship-card__icon">🚀</div>
              <div className="ship-card__title">
                <h4>{item.product.name}</h4>
                <span className="ship-card__meta">Type #{item.product.type_id}</span>
              </div>
              <div className="ship-card__qty">
                <label>Qty</label>
                <input type="number" min={1} value={item.qty} onChange={e => updateQty(index, Number(e.target.value || 1))} />
              </div>
              <button className="ship-card__remove" onClick={() => remove(item.product.type_id)} aria-label="Remove ship">×</button>
            </header>

            <div className="ship-card__metrics">
              <div>
                <span className="ship-card__metric-label">Cost</span>
                <span className="ship-card__metric-value">{item.cost !== undefined ? Math.round(item.cost).toLocaleString() : '—'} ISK</span>
              </div>
              <div>
                <span className="ship-card__metric-label">Net Sale</span>
                <span className="ship-card__metric-value">{item.saleNet !== undefined ? Math.round(item.saleNet).toLocaleString() : '—'} ISK</span>
              </div>
              <div>
                <span className="ship-card__metric-label">Profit</span>
                <span className="ship-card__metric-value accent">{item.profit !== undefined ? Math.round(item.profit).toLocaleString() : '—'} ISK</span>
              </div>
              <div>
                <span className="ship-card__metric-label">Spread</span>
                <span className="ship-card__metric-value">{item.quote ? Math.round(item.quote.spread).toLocaleString() : '—'} ISK</span>
              </div>
            </div>

            <div className="ship-card__chart">
              <PriceSparkline typeId={item.product.type_id} regionId={settings.regionId} />
            </div>

            {item.quote && (
              <div className="ship-card__market">
                <div>
                  <span className="ship-card__metric-label">Bid</span>
                  <span className="ship-card__metric-value">{Math.round(item.quote.bid).toLocaleString()}</span>
                </div>
                <div>
                  <span className="ship-card__metric-label">Ask</span>
                  <span className="ship-card__metric-value">{Math.round(item.quote.ask).toLocaleString()}</span>
                </div>
                <div>
                  <span className="ship-card__metric-label">Depth 5%</span>
                  <span className="ship-card__metric-value">{Math.round(item.quote.depth_qty_5pct).toLocaleString()}</span>
                </div>
                <div>
                  <span className="ship-card__metric-label">Depth 1%</span>
                  <span className="ship-card__metric-value">{Math.round(item.quote.depth_qty_1pct).toLocaleString()}</span>
                </div>
              </div>
            )}

            <footer className="ship-card__footer">
              <button className="btn" onClick={() => toggleExpanded(index)}>{item.expanded ? 'Collapse BOM' : 'Expand BOM'}</button>
            </footer>
            {item.expanded && item.tree && (
              <div className="ship-card__tree">{renderTree(item.tree)}</div>
            )}
          </article>
        ))}
        {!basket.length && (
          <div className="ship-basket__empty">Add a ship to begin planning.</div>
        )}
      </div>
    </div>
  )
}

function renderTree(node: TreeNode, depth = 0): JSX.Element {
  return (
    <div key={`${node.product_id}-${depth}`} style={{ marginLeft: depth * 12 }}>
      <div className="ship-card__tree-node">Product {node.product_id} ({node.activity})</div>
      {node.materials.map(mat => (
        <div key={`${node.product_id}-${mat.type_id}`} className="ship-card__tree-material" style={{ marginLeft: 12 }}>
          • {mat.type_id} × {mat.qty}
        </div>
      ))}
      {node.children?.map(child => renderTree(child, depth + 1))}
    </div>
  )
}

