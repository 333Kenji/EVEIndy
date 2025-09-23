import React from 'react'

type Point = { ts: string; mid: string | null }

export default function PriceSparkline({ typeId, regionId }: { typeId: number; regionId: number }) {
  const [points, setPoints] = React.useState<Point[]>([])
  React.useEffect(() => {
    fetch(`/prices/history?type_id=${typeId}&region_id=${regionId}&days=7`).then(r => r.ok ? r.json() : Promise.reject()).then(d => setPoints(d.points || [])).catch(() => setPoints([]))
  }, [typeId, regionId])

  if (!points.length) return <div style={{ opacity: 0.6 }}>No history</div>
  const width = 240, height = 64, pad = 6
  const mids = points.map(p => (p.mid ? Number(p.mid) : 0))
  const min = Math.min(...mids), max = Math.max(...mids)
  const scaleX = (i: number) => pad + (i * (width - 2 * pad)) / Math.max(1, points.length - 1)
  const scaleY = (v: number) => height - pad - (max === min ? 0 : ((v - min) * (height - 2 * pad)) / (max - min))
  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(i)} ${scaleY(Number(p.mid || 0))}`).join(' ')
  const areaPath = `${linePath} L ${scaleX(points.length - 1)} ${height - pad} L ${scaleX(0)} ${height - pad} Z`
  const latest = points[points.length - 1]
  const latestMid = latest?.mid ? Number(latest.mid).toLocaleString() : '—'

  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <defs>
        <linearGradient id={`spark-${typeId}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="rgba(34,211,238,0.45)" />
          <stop offset="100%" stopColor="rgba(34,211,238,0.05)" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#spark-${typeId})`} stroke="none" />
      <path d={linePath} fill="none" stroke="#22d3ee" strokeWidth={2} strokeLinecap="round" />
      <text x={width - pad} y={pad + 10} textAnchor="end" fontSize={11} fill="rgba(230,232,240,0.8)">{latestMid}</text>
    </svg>
  )
}

