import React, { forwardRef } from 'react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className = '', id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined)

    return (
      <div className="flex flex-col gap-1 w-full text-left">
        {label && (
          <label
            htmlFor={inputId}
            className="font-mono text-[11px] uppercase tracking-wider flex justify-between"
            style={{
              fontFamily: "var(--f-mono, 'Geist Mono', monospace)",
              color: 'var(--ink-72, rgba(40,40,40,0.72))',
            }}
          >
            <span>{label}</span>
            {props.required && <span style={{ color: 'var(--accent, #fa3600)' }}>*</span>}
          </label>
        )}
        <input
          id={inputId}
          ref={ref}
          className={`h-10 px-3 font-mono text-[13px] bg-[var(--paper)] text-[var(--ink)] transition-colors ${className}`}
          style={{
            border: error
              ? '1px solid var(--accent, #fa3600)'
              : '1px solid var(--line, rgba(40,40,40,0.22))',
            fontFamily: "var(--f-mono, 'Geist Mono', monospace)",
            outline: 'none',
            borderRadius: '0px',
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = 'var(--accent, #fa3600)'
            props.onFocus?.(e)
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = error
              ? 'var(--accent, #fa3600)'
              : 'var(--line, rgba(40,40,40,0.22))'
            props.onBlur?.(e)
          }}
          {...props}
        />
        {error && (
          <span
            className="font-mono text-[11px]"
            style={{ color: 'var(--accent, #fa3600)' }}
          >
            {error}
          </span>
        )}
        {!error && helperText && (
          <span
            className="font-mono text-[11px]"
            style={{ color: 'var(--ink-50, rgba(40,40,40,0.5))' }}
          >
            {helperText}
          </span>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
