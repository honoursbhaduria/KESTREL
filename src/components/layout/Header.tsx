import { useEffect, useRef, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { Logo } from '~/components/ui/Logo'
import { RollLabel } from '~/components/ui/Button'
import { nav, navCta } from '~/content/site'

const NAV = nav

function NavLink({ href, children, className, onClick }: { href: string; children: React.ReactNode; className?: string; onClick?: () => void }) {
  if (href.includes('#')) return <a href={href} className={className} onClick={onClick}>{children}</a>
  return <Link to={href} className={className} onClick={onClick}>{children}</Link>
}

const Arrow = () => <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M1 7h12M8 2l5 5-5 5" /></svg>

export function Header() {
  const [openSub, setOpenSub] = useState<number | null>(null)
  const [mobile, setMobile] = useState(false)
  const [hidden, setHidden] = useState(false)
  const navRef = useRef<HTMLElement>(null)

  useEffect(() => {
    let last = window.scrollY
    const onScroll = () => {
      const y = window.scrollY
      setHidden(y > last && y > 400)
      if (y > last) setOpenSub(null)
      last = y
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    const onDown = (e: PointerEvent) => {
      const t = e.target as HTMLElement
      if (!navRef.current?.contains(t)) setOpenSub(null)
      if (!t.closest('.mobile-menu, .menu-btn')) setMobile(false)
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') { setOpenSub(null); setMobile(false) } }
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('pointerdown', onDown); document.removeEventListener('keydown', onKey) }
  }, [])

  useEffect(() => { document.documentElement.classList.toggle('menu-open', mobile) }, [mobile])

  const close = () => { setMobile(false); setOpenSub(null) }

  return (
    <>
      <header className={`header${hidden && !mobile ? ' is-hidden' : ''}`}>
        <div className="header__logo"><Logo onClick={close} /></div>

        <nav className="nav" aria-label="Primary" ref={navRef}>
          {NAV.map((item, i) => (
            <div className="nav__item" key={item.label}>
              {'children' in item ? (
                <>
                  <button className="nav__link mono" aria-expanded={openSub === i} aria-controls={`sub-${i}`} onClick={() => setOpenSub(openSub === i ? null : i)}>
                    <RollLabel>{item.label}</RollLabel>
                    <span className="nav__corner" aria-hidden="true" />
                  </button>
                  <ul className={`nav__sub${openSub === i ? ' is-open' : ''}`} id={`sub-${i}`}>
                    {item.children.map((c) => (
                      <li key={c.label}><NavLink href={c.href} onClick={close}>{c.label}</NavLink></li>
                    ))}
                  </ul>
                </>
              ) : (
                <NavLink href={item.href} className="nav__link mono" onClick={close}><RollLabel>{item.label}</RollLabel></NavLink>
              )}
            </div>
          ))}
          <div className="nav__item nav__item--cta">
            <a href={navCta.href} className="nav__link mono" onClick={close}><RollLabel>{navCta.label}</RollLabel><Arrow /></a>
          </div>
        </nav>

        <button className={`menu-btn mono${mobile ? ' is-open' : ''}`} aria-expanded={mobile} aria-controls="mobile-menu" onClick={() => setMobile((m) => !m)}>
          <RollLabel>{mobile ? 'Close' : 'Menu'}</RollLabel>
          <span className="menu-btn__icon" aria-hidden="true"><span /><span /><span /></span>
        </button>

        {/* Mobile: a stack of cells dropping from the menu cell */}
        <nav className={`mobile-menu${mobile ? ' is-open' : ''}`} id="mobile-menu" aria-label="Mobile" aria-hidden={!mobile}>
          <ul>
            {NAV.map((item) => ('children' in item ? { label: item.label, href: item.children[0].href, sub: true } : { ...item, sub: false })).map((item, i) => (
              <li key={item.label} style={{ '--i': i } as React.CSSProperties}>
                <NavLink href={item.href} onClick={close} className="mobile-menu__link mono">
                  <span>{item.label}</span>
                  {item.sub && <span className="nav__corner" aria-hidden="true" />}
                </NavLink>
              </li>
            ))}
            <li className="mobile-menu__cta" style={{ '--i': NAV.length } as React.CSSProperties}>
              <a href={navCta.href} onClick={close} className="mobile-menu__link mono">
                <span>{navCta.label}</span><Arrow />
              </a>
            </li>
          </ul>
        </nav>
      </header>
    </>
  )
}
