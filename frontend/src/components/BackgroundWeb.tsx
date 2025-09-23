import React, { useEffect, useRef } from 'react'

type Node = { x: number; y: number; vx: number; vy: number }

type Gradient = { stops: string[] }

export default function BackgroundWeb({
  density = 1,
  velocity = 1,
  filamentAmplitude = 1,
  gradient = { stops: ['#1e3a8a', '#4c1d95'] },
}: {
  density?: number
  velocity?: number
  filamentAmplitude?: number
  gradient?: Gradient
}) {
  const ref = useRef<HTMLCanvasElement | null>(null)
  const raf = useRef<number | null>(null)
  const nodes = useRef<Node[]>([])

  useEffect(() => {
    const canvas = ref.current!
    const ctx = canvas.getContext('2d')!
    let w = (canvas.width = window.innerWidth)
    let h = (canvas.height = window.innerHeight)

    const init = () => {
      const base = Math.min(120, Math.floor((w * h) / 16000))
      const count = Math.max(50, Math.floor(base * density))
      nodes.current = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.3 * velocity,
        vy: (Math.random() - 0.5) * 0.3 * velocity
      }))
    }

    const draw = () => {
      ctx.clearRect(0, 0, w, h)
      // gradient stroke
      const grad = ctx.createLinearGradient(0, 0, w, h)
      gradient.stops.forEach((c, i) => grad.addColorStop(i / Math.max(1, gradient.stops.length - 1), c))
      ctx.strokeStyle = grad
      ctx.fillStyle = 'rgba(255,255,255,0.6)'

      const ns = nodes.current
      for (let i = 0; i < ns.length; i++) {
        const a = ns[i]
        a.x += a.vx; a.y += a.vy
        if (a.x < 0 || a.x > w) a.vx *= -1
        if (a.y < 0 || a.y > h) a.vy *= -1
        // node
        ctx.beginPath(); ctx.arc(a.x, a.y, 1.2, 0, Math.PI * 2); ctx.fill()
        // filaments
        for (let j = i + 1; j < ns.length; j++) {
          const b = ns[j]
          const dx = a.x - b.x, dy = a.y - b.y
          const d2 = dx * dx + dy * dy
          const limit = 160 * filamentAmplitude
          if (d2 < limit * limit) {
            ctx.globalAlpha = Math.max(0.05, 1 - d2 / (limit * limit))
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke()
            ctx.globalAlpha = 1
          }
        }
      }
      raf.current = requestAnimationFrame(draw)
    }

    const onResize = () => { w = canvas.width = window.innerWidth; h = canvas.height = window.innerHeight; init() }
    init(); draw(); window.addEventListener('resize', onResize)
    const onVis = () => { if (document.hidden) { if (raf.current) cancelAnimationFrame(raf.current) } else { draw() } }
    document.addEventListener('visibilitychange', onVis)
    return () => { window.removeEventListener('resize', onResize); document.removeEventListener('visibilitychange', onVis); if (raf.current) cancelAnimationFrame(raf.current) }
  }, [])

  return <canvas
    ref={ref}
    data-density={density}
    data-velocity={velocity}
    data-filament={filamentAmplitude}
    data-gradient={gradient.stops.join(',')}
    style={{ position: 'fixed', inset: 0, zIndex: 0, opacity: 0.5, pointerEvents: 'none' }}
  />
}
