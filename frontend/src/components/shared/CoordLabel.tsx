import React from 'react'

interface CoordLabelProps {
  axis?: 'X' | 'Y' | 'Z'
  value: number | string
  unit?: string
  className?: string
}

export const CoordLabel: React.FC<CoordLabelProps> = ({
  axis,
  value,
  unit = 'MM',
  className = '',
}) => {
  return (
    <span
      className={`inline-flex items-center gap-1 font-mono text-[11px] tabular-nums tracking-wider ${className}`}
      style={{
        fontFamily: "var(--f-mono, 'Geist Mono', monospace)",
        color: 'var(--ink-72, rgba(40,40,40,0.72))',
      }}
    >
      {axis && <span style={{ color: 'var(--ink-50, rgba(40,40,40,0.5))' }}>{axis}:</span>}
      <b style={{ color: 'var(--ink, #282828)', fontWeight: 600 }}>{value}</b>
      {unit && <span style={{ color: 'var(--ink-50, rgba(40,40,40,0.5))', fontSize: '10px' }}>{unit}</span>}
    </span>
  )
}

interface BracketLabelProps {
  text: string
  className?: string
  accent?: boolean
}

export const BracketLabel: React.FC<BracketLabelProps> = ({
  text,
  className = '',
  accent = false,
}) => {
  return (
    <span
      className={`inline-flex items-center font-mono text-[11px] uppercase tracking-wider ${className}`}
      style={{
        fontFamily: "var(--f-mono, 'Geist Mono', monospace)",
        color: accent ? 'var(--accent, #fa3600)' : 'var(--ink-50, rgba(40,40,40,0.5))',
      }}
    >
      [{text}]
    </span>
  )
}
