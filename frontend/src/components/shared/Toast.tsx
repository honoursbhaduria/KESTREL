import React from 'react'

export type ToastType = 'info' | 'success' | 'warning' | 'error'

interface ToastProps {
  message: string
  type?: ToastType
  onClose?: () => void
  className?: string
}

export const Toast: React.FC<ToastProps> = ({
  message,
  type = 'info',
  onClose,
  className = '',
}) => {
  const borderColors = {
    info: 'var(--ink)',
    success: 'var(--ok, #3c8a52)',
    warning: 'var(--warn, #c98a00)',
    error: 'var(--accent, #fa3600)',
  }

  const prefix = {
    info: '[INFO]',
    success: '[OK]',
    warning: '[WARN]',
    error: '[ERR]',
  }

  return (
    <div
      className={`flex items-center justify-between gap-3 px-4 py-2.5 bg-[var(--paper)] border font-mono text-[12px] shadow-[0_3px_0_var(--ink)] ${className}`}
      style={{
        borderColor: borderColors[type],
      }}
    >
      <div className="flex items-center gap-2">
        <span style={{ color: borderColors[type], fontWeight: 700 }}>
          {prefix[type]}
        </span>
        <span style={{ color: 'var(--ink)' }}>{message}</span>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="text-[var(--ink-50)] hover:text-[var(--accent)] font-mono text-[11px]"
        >
          [x]
        </button>
      )}
    </div>
  )
}
