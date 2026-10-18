import React from 'react'

interface DataRowProps {
  label: string
  value: React.ReactNode
  unit?: string
  className?: string
  borderBottom?: boolean
  accent?: boolean
}

export const DataRow: React.FC<DataRowProps> = ({
  label,
  value,
  unit,
  className = '',
  borderBottom = true,
  accent = false,
}) => {
  return (
    <div
      className={`flex items-baseline justify-between py-1.5 text-[12px] font-mono ${className}`}
      style={{
        borderBottom: borderBottom ? '1px dashed var(--line, rgba(40,40,40,0.22))' : 'none',
        fontFamily: "var(--f-mono, 'Geist Mono', monospace)",
      }}
    >
      <span style={{ color: 'var(--ink-50, rgba(40,40,40,0.5))' }}>
        {label}
      </span>
      <span
        className="flex items-baseline gap-1"
        style={{
          color: accent ? 'var(--orange, #fa3600)' : 'var(--ink, #282828)',
          fontWeight: accent ? 600 : 500,
        }}
      >
        {value}
        {unit && <span style={{ color: 'var(--ink-50, rgba(40,40,40,0.5))', fontSize: '10px' }}>{unit}</span>}
      </span>
    </div>
  )
}
