import React from 'react'

type Node = { id: string; label?: string }
type Edge = { source: string; target: string }

export default function ChangeGraph({ nodes, edges }: { nodes: Node[]; edges: Edge[] }) {
  // responsive svg using viewBox
  const width = Math.max(300, nodes.length * 120)
  const height = 260
  const xStep = Math.max(120, Math.floor(width / Math.max(1, nodes.length)))

  const positions = nodes.reduce<Record<string, { x: number; y: number }>>((acc, n, i) => {
    acc[n.id] = { x: 60 + i * xStep, y: height / 2 }
    return acc
  }, {})

  return (
    <div style={{ overflowX: 'auto' }}>
      <svg width={Math.min(1000, width)} height={height} viewBox={`0 0 ${width} ${height}`} style={{ border: '1px solid var(--border-subtle)', background: 'transparent' }}>
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="6" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <g>
          {edges.map((e, i) => {
            const a = positions[e.source]
            const b = positions[e.target]
            if (!a || !b) return null
            return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="var(--border)" strokeWidth={2} strokeOpacity={0.6} />
          })}

          {nodes.map((n) => {
            const p = positions[n.id]
            if (!p) return null
            return (
              <g key={n.id}>
                <rect x={p.x - 60} y={p.y - 26} width={120} height={52} rx={8} fill="var(--intelligence)" stroke="var(--brand)" strokeWidth={1.5} filter="url(#glow)" />
                <text x={p.x} y={p.y} dominantBaseline="middle" textAnchor="middle" style={{ fontSize: 12, fill: 'var(--text-primary)', fontWeight: 700 }}>
                  {n.label ?? n.id}
                </text>
              </g>
            )
          })}
        </g>
      </svg>
    </div>
  )
}
