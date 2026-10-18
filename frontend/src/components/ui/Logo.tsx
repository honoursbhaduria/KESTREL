import { Link } from '@tanstack/react-router'
import { brand } from '~/content/site'

export function LogoMark({ className = 'logo__mark' }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden="true">
      <path d="M4 34 20 6l16 28Z" />
      <path d="M10.5 23h19M20 6v28" />
    </svg>
  )
}

export function Logo({ onClick }: { onClick?: () => void }) {
  return (
    <Link to="/" className="logo" aria-label={`${brand.name} home`} onClick={onClick}>
      {brand.logo ? <img src={brand.logo.src} alt="" className="logo__img" /> : <LogoMark />}
      <span>{brand.name}</span>
    </Link>
  )
}
