import { useEffect, useRef, useState } from 'react'
import { SplitText } from '~/components/ui/SplitText'
import { Ruler } from '~/components/ui/Ruler'
import { PlanCanvas, ISSUES, type Issue } from '~/lib/planCanvas'
import { hero } from '~/content/site'
import { gsap, prefersReducedMotion } from '~/lib/gsap'
import { useGsap } from '~/hooks/useGsap'
import { whenPageVisible, onAppReady } from '~/lib/ready'
import { DUR_SLOW, EASE, EASE_SLOW, STAGGER_TEXT, TEXT_FROM, TEXT_TO } from '~/lib/motion'

const TICKER_ICONS = ['M3 3h10v10H3zM3 8h10', 'M8 2v12M2 8h12', 'M2 8l4 4 8-8', 'M8 2l6 6-6 6-6-6z', 'M3 13 8 3l5 10z']

/** Endless strip of value props under the hero, duplicated so the loop is seamless. */
function Ticker() {
  const items = [...hero.ticker, ...hero.ticker].map((t, i) => [t, TICKER_ICONS[i % TICKER_ICONS.length]] as const)
  return (
    <div className="ticker" aria-label={hero.ticker.join(', ')}>
      <div className="ticker__track" aria-hidden="true">
        {[0, 1].map((k) => (
          <div className="ticker__group" key={k}>
            {items.map(([t, d], i) => (
              <span className="ticker__item mono" key={i}>
                <svg viewBox="0 0 16 16"><path d={d} /></svg>{t}
              </span>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export function Hero() {
  const ref = useRef<HTMLElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const xRef = useRef<HTMLElement>(null)
  const yRef = useRef<HTMLElement>(null)
  const [found, setFound] = useState<Issue[]>([])
  const crossRef = useRef<HTMLDivElement>(null)

  // Full-bleed crosshair + px readout + hint tooltip, written straight to the DOM
  useEffect(() => {
    const wrap = canvasRef.current?.parentElement
    const cross = crossRef.current
    if (!wrap || !cross || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) return
    const px = cross.querySelector<HTMLElement>('.cross__px')!
    const move = (e: PointerEvent) => {
      const r = wrap.getBoundingClientRect()
      const x = Math.round(e.clientX - r.left)
      const y = Math.round(e.clientY - r.top)
      cross.style.setProperty('--x', `${x}px`)
      cross.style.setProperty('--y', `${y}px`)
      px.textContent = `X: ${x}PX\nY: ${y}PX`
    }
    const enter = () => cross.classList.add('is-on')
    const leave = () => cross.classList.remove('is-on')
    const down = () => cross.classList.add('is-drag')
    const up = () => cross.classList.remove('is-drag')
    wrap.addEventListener('pointermove', move)
    wrap.addEventListener('pointerenter', enter)
    wrap.addEventListener('pointerleave', leave)
    wrap.addEventListener('pointerdown', down)
    window.addEventListener('pointerup', up)
    return () => {
      wrap.removeEventListener('pointermove', move)
      wrap.removeEventListener('pointerenter', enter)
      wrap.removeEventListener('pointerleave', leave)
      wrap.removeEventListener('pointerdown', down)
      window.removeEventListener('pointerup', up)
    }
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const plan = new PlanCanvas(canvas, {
      reduced: prefersReducedMotion(),
      overlayOnly: !!hero.image,
      onMove: (x, y) => {
        // Written straight to the DOM: this fires on every pointer move
        if (xRef.current) xRef.current.textContent = String(x)
        if (yRef.current) yRef.current.textContent = String(y)
      },
      onReveal: (issue) => setFound((f) => [...f, issue]),
    })
    const off = onAppReady(() => plan.playIntro(1.6))
    return () => { off(); plan.destroy() }
  }, [])

  useGsap(ref, ({ reduced, el }) => {
    if (reduced) return
    const tl = gsap.timeline({ paused: true, delay: 0.2 })
      .fromTo(el.querySelectorAll('.split-word > span'), TEXT_FROM, TEXT_TO)
      .fromTo(el.querySelectorAll('.hero__reveal'), { autoAlpha: 0, y: 16 }, { autoAlpha: 1, y: 0, duration: 0.8, ease: EASE, stagger: STAGGER_TEXT * 4 }, '-=0.5')
      .fromTo(el.querySelectorAll('.ruler'), { scaleX: 0 }, { scaleX: 1, duration: DUR_SLOW, ease: EASE_SLOW, transformOrigin: 'left' }, 0)
    return whenPageVisible(() => tl.play())
  })

  return (
    <section className="hero sec" id="top" ref={ref}>
      <div className="hero__stage">
        <Ruler />
        <div className="hero__canvas-wrap">
          {hero.image && <img className="hero__img" src={hero.image.src} alt={hero.image.alt} draggable={false} />}
          <canvas
            ref={canvasRef}
            className="hero__canvas"
            tabIndex={0}
            role="img"
            aria-label="Building elevation. Click and drag, or focus and use the arrow keys, to scan for design issues."
          />
          <div className="cross" ref={crossRef} aria-hidden="true">
            <span className="cross__v" />
            <span className="cross__h" />
            <span className="cross__plus" />
            <span className="cross__px mono">X: 0PX{'\n'}Y: 0PX</span>
            <span className="cross__tip mono">{found.length === ISSUES.length ? hero.hintDone : hero.hint}</span>
          </div>
          <div className="hero__coords mono hero__reveal" aria-hidden="true">
            <span>X: <b ref={xRef}>0</b> MM</span>
            <span>Y: <b ref={yRef}>0</b> MM</span>
          </div>
          <ul className="hero__found" aria-live="polite">
            {found.slice(-2).map((i) => (
              <li className="flag" key={i.id}>
                <div className="flag__head mono"><span>{i.code}</span><span>Flagged</span></div>
                <p className="flag__text">{i.text}</p>
              </li>
            ))}
          </ul>
          <p className="hero__hint mono hero__reveal" aria-hidden="true">
            <i />
            {found.length === 0 ? 'Click and drag to scan the drawing' : `${found.length} of ${ISSUES.length} issues found`}
          </p>
        </div>
        <Ruler />
      </div>

      <div className="hero__bottom">
        <div className="hero__title">
          <SplitText as="h1" className="h1" text={hero.title} />
        </div>
        <p className="hero__desc body hero__reveal">{hero.description}</p>
        <a href={hero.discover.href} className="hero__more mono hero__reveal">
          <span>{hero.discover.label}</span>
          <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M1 7h12M8 2l5 5-5 5" /></svg>
        </a>
      </div>
      <Ticker />
    </section>
  )
}
