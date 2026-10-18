import React from 'react'

interface GridBackgroundProps {
  children?: React.ReactNode
  className?: string
  gridSize?: number
  withFrame?: boolean
}

export const GridBackground: React.FC<GridBackgroundProps> = ({
  children,
  className = '',
  gridSize = 24,
  withFrame = false,
}) => {
  return (
    <div
      className={`relative w-full ${className}`}
      style={{
        backgroundImage: `
          linear-gradient(to right, var(--line-soft, rgba(40,40,40,0.08)) 1px, transparent 1px),
          linear-gradient(to bottom, var(--line-soft, rgba(40,40,40,0.08)) 1px, transparent 1px)
        `,
        backgroundSize: `${gridSize}px ${gridSize}px`,
        border: withFrame ? '1px solid var(--line, rgba(40,40,40,0.22))' : 'none',
      }}
    >
      {withFrame && (
        <>
          <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-[var(--ink)]" />
          <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-[var(--ink)]" />
          <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-[var(--ink)]" />
          <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-[var(--ink)]" />
        </>
      )}
      {children}
    </div>
  )
}
