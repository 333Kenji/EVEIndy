import React from 'react'

type Point = { ts: string; mid: string | null }

export default function PriceSparkline({ typeId, regionId }: { typeId: number; regionId: number }) {
  const [points, setPoints] = React.useState<Point[]>([])
  React.useEffect(() => {
    fetch(`/prices/history?type_id=${typeId}&region_id=${regionId}&days=7`).then(r => r.ok ? r.json() : Promise.reject()).then(d => setPoints(d.points || [])).catch(() => setPoints([]))
  }, [typeId, regionId])

  if (!points.length) return <div style={{ opacity: 0.6 }}>No history</div>
  const width = 240, height = 60, pad = 6
  const mids = points.map(p => (p.mid ? Number(p.mid) : 0))
  const min = Math.min(...mids), max = Math.max(...mids)
  const scaleX = (i: number) => pad + (i * (width - 2 * pad)) / Math.max(1, points.length - 1)
  const scaleY = (v: number) => height - pad - (max === min ? 0 : ((v - min) * (height - 2 * pad)) / (max - min))
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(i)} ${scaleY(Number(p.mid || 0))}`).join(' ')

  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <path d={path} fill="none" stroke="#22d3ee" strokeWidth={2} />
    </svg>
  )
}

