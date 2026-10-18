import { useState, type FormEvent } from 'react'
import { Link } from '@tanstack/react-router'
import { LogoMark } from '~/components/ui/Logo'
import { Ruler } from '~/components/ui/Ruler'
import { brand, footer } from '~/content/site'

function FLink({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) {
  if (href.startsWith('/') && !href.includes('#')) return <Link to={href} className={className} activeOptions={{ exact: true }} activeProps={{ className: 'active' }}>{children}</Link>
  return <a href={href} className={className}>{children}</a>
}

/** Outlined wordmark with drafting construction lines. */
function Wordmark() {
  const guides = [18, 50, 112, 144]
  return (
    <svg viewBox="0 0 1000 160" role="img" aria-label={brand.name}>
      {guides.map((y) => <line key={y} className="guide" x1="0" x2="1000" y1={y} y2={y} strokeDasharray="2 6" />)}
      <text x="500" y="144" textAnchor="middle" fontSize="176" textLength="960" lengthAdjust="spacingAndGlyphs">{footer.wordmark}</text>
    </svg>
  )
}

export function Footer() {
  const [sent, setSent] = useState(false)
  const subscribe = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const input = e.currentTarget.elements.namedItem('fsub') as HTMLInputElement
    if (input.checkValidity()) { setSent(true); e.currentTarget.reset() } else input.focus()
  }

  return (
    <footer className="footer">
      <div className="footer__grid">
        <div className="fcell fcell--statement"><p className="h5">{brand.tagline}</p></div>
        {footer.columns.map((col) => (
          <nav className="fcell" aria-label={col.title} key={col.title}>
            <p className="mono">{col.title}</p>
            {col.links.map((l) => <FLink href={l.href} key={l.label}>{l.label}</FLink>)}
          </nav>
        ))}
        <div className="fcell fcell--logo"><LogoMark className="" /></div>

        <div className="fcell fcell--sub">
          <div>
            <p className="mono">{footer.subscribeTitle}</p>
            <p>{sent ? footer.subscribeDone : footer.subscribeBody}</p>
          </div>
          <form className="fsub" onSubmit={subscribe} noValidate>
            <label htmlFor="fsub" className="sr-only">Email address</label>
            <input id="fsub" name="fsub" type="email" required placeholder="Enter your email" autoComplete="email" />
            <button type="submit" aria-label="Subscribe"><svg viewBox="0 0 14 14"><path d="M1 7h12M8 2l5 5-5 5" /></svg></button>
          </form>
        </div>
        <div className="fcell">
          <p className="mono">{footer.location.title}</p>
          <p style={{ color: 'var(--ink)' }}>{footer.location.lines.map((l, i) => <span key={l}>{i > 0 && <br />}{l}</span>)}</p>
        </div>
        <div className="fcell">
          <p className="mono">{footer.contactTitle}</p>
          <a href={`mailto:${brand.email}`} className="accent">{brand.email}</a>
        </div>
        <div className="fcell fcell--social">
          <p className="mono">Social</p>
          {footer.social.map((l) => <a href={l.href} key={l.label}>{l.label}</a>)}
        </div>
      </div>

      <Ruler />
      <div className="wordmark"><Wordmark /></div>
      <Ruler />

      <div className="footer__base bt">
        <span className="mono">© {new Date().getFullYear()} {brand.copyright}</span>
        <div className="footer__legal">
          {footer.legal.map((l) => <FLink href={l.href} key={l.label}>{l.label}</FLink>)}
        </div>
      </div>
    </footer>
  )
}
