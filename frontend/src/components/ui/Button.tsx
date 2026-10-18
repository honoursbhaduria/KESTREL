import type { ComponentPropsWithoutRef, ReactNode } from 'react'

type Variant = 'accent' | 'ghost' | 'plain'
type Icon = 'arrow' | 'down' | null

export function RollLabel({ children }: { children: string }) {
  return (
    <span className="roll" data-text={children}>
      <span className="roll__inner">{children}</span>
    </span>
  )
}

function ButtonIcon({ icon }: { icon: Icon }) {
  if (!icon) return null
  return (
    <span className="btn__icon" aria-hidden="true">
      <span className="btn__icon-track">
        {[0, 1].map((k) => (
          <svg viewBox="0 0 12 12" key={k}>
            {icon === 'arrow' ? <path d="M2 10 10 2M4 2h6v6" /> : <path d="M6 1v10M2 7l4 4 4-4" />}
          </svg>
        ))}
      </span>
    </span>
  )
}

type Common = { label: string; variant?: Variant; icon?: Icon; size?: 'sm' | 'md'; children?: ReactNode }

export function ButtonLink({
  label, variant = 'accent', icon = 'arrow', size = 'md', className = '', ...rest
}: Common & ComponentPropsWithoutRef<'a'>) {
  return (
    <a className={`btn btn--${variant} btn--${size} ${className}`} {...rest}>
      <span className="btn__bg" aria-hidden="true" />
      <RollLabel>{label}</RollLabel>
      <ButtonIcon icon={icon} />
    </a>
  )
}

export function Button({
  label, variant = 'accent', icon = 'arrow', size = 'md', className = '', type = 'button', ...rest
}: Common & ComponentPropsWithoutRef<'button'>) {
  return (
    <button type={type} className={`btn btn--${variant} btn--${size} ${className}`} {...rest}>
      <span className="btn__bg" aria-hidden="true" />
      <RollLabel>{label}</RollLabel>
      <ButtonIcon icon={icon} />
    </button>
  )
}
