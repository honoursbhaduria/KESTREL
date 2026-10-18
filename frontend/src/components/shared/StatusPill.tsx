import React from 'react'

export type StatusType = 'pass' | 'review' | 'fail'

interface StatusPillProps {
  status: StatusType
  label?: string
  className?: string
}

export const StatusPill: React.FC<StatusPillProps> = ({ status, label, className = '' }) => {
  const displayLabel = label || (status === 'pass' ? 'Pass' : status === 'review' ? 'Review' : 'Fail')

  const stylesByStatus = {
    pass: {
      color: '#3c8a52',
      border: '1px solid rgba(60, 138, 82, 0.4)',
      bg: 'rgba(60, 138, 82, 0.08)',
      dotBg: '#3c8a52',
    },
    review: {
      color: '#c98a00',
      border: '1px solid rgba(201, 138, 0, 0.4)',
      bg: 'rgba(201, 138, 0, 0.08)',
      dotBg: '#c98a00',
    },
    fail: {
      color: '#fa3600',
      border: '1px solid rgba(250, 54, 0, 0.4)',
      bg: 'rgba(250, 54, 0, 0.08)',
      dotBg: '#fa3600',
    },
  }

  const s = stylesByStatus[status]

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider font-semibold ${className}`}
      style={{
        color: s.color,
        border: s.border,
        backgroundColor: s.bg,
        fontFamily: "var(--f-mono, 'Geist Mono', monospace)",
        letterSpacing: '0.04em',
        borderRadius: '2px',
      }}
    >
      <span
        style={{
          width: '5px',
          height: '5px',
          borderRadius: '50%',
          backgroundColor: s.dotBg,
          display: 'inline-block',
        }}
      />
      {displayLabel}
    </span>
  )
}
