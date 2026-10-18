import React from 'react'

interface CardProps {
  children: React.ReactNode
  title?: string
  badge?: React.ReactNode
  subtitle?: string
  className?: string
  darkHeader?: boolean
  onClick?: () => void
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  badge,
  subtitle,
  className = '',
  darkHeader = false,
  onClick,
}) => {
  return (
    <div
      onClick={onClick}
      className={`bg-[var(--paper)] border border-[var(--line)] transition-all ${onClick ? 'cursor-pointer hover:translate-y-[-1px]' : ''} ${className}`}
      style={{
        boxShadow: '0 4px 0 var(--ink, #282828)',
      }}
    >
      {(title || badge) && (
        <div
          className={`px-3 py-2 flex items-center justify-between border-b border-[var(--line)] ${darkHeader ? 'bg-[var(--ink)] text-white' : 'bg-[var(--paper-2)] text-[var(--ink)]'}`}
        >
          <div>
            <div className="font-mono text-[12px] font-semibold uppercase tracking-wider">
              {title}
            </div>
            {subtitle && (
              <div className="font-mono text-[10px] opacity-70">
                {subtitle}
              </div>
            )}
          </div>
          {badge && <div>{badge}</div>}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  )
}
