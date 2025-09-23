import React from 'react'

type Indicator = {
  ma: string | number
  volatility: string | number
  bollinger: { middle: string | number; upper: string | number; lower: string | number }
}

const AnalyticsPane: React.FC = () => {
  const [typeId, setTypeId] = React.useState(603)
  const [regionId, setRegionId] = React.useState(10000002)
  const [indicators, setIndicators] = React.useState<Indicator | null>(null)
  const [spp, setSpp] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(false)

  const load = React.useCallback(async () => {
    setLoading(true)
    try {
      const [indRes, sppRes] = await Promise.all([
        fetch(`/analytics/indicators?type_id=${typeId}&region_id=${regionId}`),
        fetch('/analytics/spp_plus', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type_id: typeId, region_id: regionId, lead_time_days: 1, horizon_days: 3, batch_options: [1, 2, 3] }),
        }),
      ])
      const indData = indRes.ok ? await indRes.json() : null
      const sppData = sppRes.ok ? await sppRes.json() : null
      setIndicators(indData)
      setSpp(sppData)
    } finally {
      setLoading(false)
    }
  }, [typeId, regionId])

  React.useEffect(() => { load() }, [load])

  return (
    <div className="pane-analytics">
      <div className="pane-analytics__filters">
        <label>
          Type ID
          <input type="number" value={typeId} onChange={(e) => setTypeId(Number(e.target.value || 0))} />
        </label>
        <label>
          Region ID
          <input type="number" value={regionId} onChange={(e) => setRegionId(Number(e.target.value || 0))} />
        </label>
        <button className="btn" onClick={load} disabled={loading}>Refresh</button>
      </div>
      {loading && <div style={{ opacity: 0.7 }}>Loading analytics…</div>}
      {!loading && (indicators || spp) && (
        <div className="pane-analytics__grid">
          {indicators && (
            <div className="pane-analytics__card">
              <h4>Indicators</h4>
              <div>Moving Average: {Number(indicators.ma || 0).toFixed(2)}</div>
              <div>Volatility: {Number(indicators.volatility || 0).toFixed(4)}</div>
              <div>Bollinger Upper: {Number(indicators.bollinger.upper || 0).toFixed(2)}</div>
              <div>Bollinger Lower: {Number(indicators.bollinger.lower || 0).toFixed(2)}</div>
            </div>
          )}
          {spp && (
            <div className="pane-analytics__card">
              <h4>SPP⁺ Forecast</h4>
              <div>Probability: {Number(spp.spp || 0).toFixed(4)}</div>
              <div>Recommended Batch: {spp.recommended_batch}</div>
              <div>Queue Depth Projection: {spp.diagnostics?.queue_at_listing}</div>
            </div>
          )}
        </div>
      )}
      {!loading && !indicators && !spp && <div style={{ opacity: 0.7 }}>No data yet. Adjust filters and refresh.</div>}
    </div>
  )
}

export default AnalyticsPane
