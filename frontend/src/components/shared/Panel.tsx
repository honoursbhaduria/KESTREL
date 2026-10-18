import React from 'react'

interface PanelProps {
  children: React.ReactNode
  header?: React.ReactNode
  footer?: React.ReactNode
  className?: string
  bordered?: boolean
}

export const Panel: React.FC<PanelProps> = ({
  children,
  header,
  footer,
  className = '',
  bordered = true,
}) => {
  return (
    <div
      className={`bg-[var(--paper)] ${bordered ? 'border border-[var(--line)]' : ''} ${className}`}
    >
      {header && (
        <div className="px-4 py-2.5 border-b border-[var(--line)] flex items-center justify-between">
          {header}
        </div>
      )}
      <div className="p-4">{children}</div>
      {footer && (
        <div className="px-4 py-2.5 border-t border-[var(--line)] bg-[var(--paper-2)]">
          {footer}
        </div>
      )}
    </div>
  )
}
