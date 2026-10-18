import React, { useEffect } from 'react'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  maxWidth?: string
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  maxWidth = 'max-w-lg',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown)
    }
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-[rgba(40,40,40,0.6)] backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Dialog Box */}
      <div
        className={`relative w-full ${maxWidth} bg-[var(--paper)] border border-[var(--ink)] shadow-[0_8px_0_var(--ink)] z-10`}
      >
        <div className="flex items-center justify-between px-4 py-3 bg-[var(--ink)] text-white">
          <span className="font-mono text-[12px] uppercase tracking-wider font-semibold">
            {title}
          </span>
          <button
            onClick={onClose}
            className="text-white hover:text-[var(--accent)] font-mono text-[13px] px-1"
            aria-label="Close"
          >
            [X]
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}
