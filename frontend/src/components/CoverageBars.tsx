import React from 'react'

type Bucket = { label: string; qty: number; days: number; color: string }

export default function CoverageBars({ buckets }: { buckets: Bucket[] }) {
  const total = buckets.reduce((s, b) => s + b.qty, 0)
  return (
    <div style={{ display: 'flex', gap: 8 }}>
      {buckets.map((b) => (
        <div key={b.label} title={`${b.label}: ${b.qty} (${b.days}d)`} style={{ flex: b.qty / (total || 1), background: b.color, minWidth: 40, height: 16 }} />
      ))}
    </div>
  )
}

