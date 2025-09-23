import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { getJSON, postJSON } from '../api/client'
import CoverageBars from '../components/CoverageBars'

type Indicators = { ma: number; bollinger: { upper: number; middle: number; lower: number }; volatility: number }

export default function Dashboard() {
  const { data: indicators } = useQuery<Indicators>({
    queryKey: ['indicators', 603],
    queryFn: () => getJSON(`/analytics/indicators?type_id=603&region_id=10000002&window=5`)
  })

  const [spp, setSpp] = React.useState<{ spp: number; recommended_batch: number } | null>(null)
  React.useEffect(() => {
    postJSON<{ spp: number; recommended_batch: number }>(`/analytics/spp_plus`, {
      type_id: 603,
      region_id: 10000002,
      lead_time_days: 1,
      horizon_days: 3,
      batch_options: [1, 2, 3]
    }).then(setSpp).catch(() => {})
  }, [])

  return (
    <div>
      <h2>Dashboard</h2>
      <section>
        <h3>Inventory Coverage</h3>
        <CoverageBars
          buckets={[
            { label: 'On-hand', qty: 10, days: 2, color: '#4ade80' },
            { label: 'At Jita', qty: 6, days: 1, color: '#60a5fa' },
            { label: 'Open Buys', qty: 3, days: 0.5, color: '#fbbf24' }
          ]}
        />
      </section>
      <section>
        <h3>Indicators</h3>
        {indicators ? (
          <pre>{JSON.stringify(indicators, null, 2)}</pre>
        ) : (
          <div>Loading…</div>
        )}
      </section>
      <section>
        <h3>SPP⁺</h3>
        {spp ? <div>SPP: {spp.spp} — Recommended batch: {spp.recommended_batch}</div> : <div>Loading…</div>}
      </section>
    </div>
  )
}

