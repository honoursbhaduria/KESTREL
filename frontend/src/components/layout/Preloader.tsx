import { useLayoutEffect, useEffect, useRef, useState } from 'react'
import { gsap } from '~/lib/gsap'
import { isAppReady, markAppReady } from '~/lib/ready'
import { prefersReducedMotion } from '~/lib/gsap'
import { DUR, EASE, EASE_IN_OUT, STAGGER_TEXT, TEXT_FROM, TEXT_TO } from '~/lib/motion'
import { preloader } from '~/content/site'
import { W, H, FIT, GROUND, SOLIDS, GLASS, FINS } from '~/lib/planCanvas'

const useIsoLayoutEffect = typeof window !== 'undefined' ? useLayoutEffect : useEffect

const SPEC = preloader.spec
const LOG = preloader.log

// Pad the viewBox so the SVG scales exactly like the hero canvas (fit × FIT, centred)
const PW = W / FIT
const PH = H / FIT
const VIEWBOX = `${-(PW - W) / 2} ${-(PH - H) / 2} ${PW} ${PH}`

/** Wireframe of the hero building, as plain line segments in drawing units. */
function wireframe(): string[] {
  const d: string[] = [`M20 ${GROUND}H980`]
  for (const [x, y, w, h] of SOLIDS) d.push(`M${x} ${y + h}V${y}H${x + w}V${y + h}`)
  for (const [x, y, w, h] of GLASS) {
    d.push(`M${x} ${y}h${w}v${h}h${-w}Z`)
    d.push(`M${x + w / 3} ${y}v${h}M${x + (2 * w) / 3} ${y}v${h}M${x} ${y + h / 2}h${w}`)
  }
  for (const fx of FINS) d.push(`M${fx} 104V236`)
  for (let i = 0; i < 8; i++) d.push(`M250 ${420 + i * 6.25}H${370 - i * 6}`)
  d.push('M560 100V88H810V100')
  return d
}
const PATHS = wireframe()

/**
 * Drawing-office preloader.
 * A scan line sweeps the sheet with a live percentage while the building's
 * wireframe is traced; a spec sheet and boot log type out. At 100% the scan
 * line splits into two guides framing the building, and the sheet dissolves
 * into the hero, whose canvas is drawn in exactly the same place.
 */
export function Preloader() {
  const ref = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const [done, setDone] = useState(isAppReady)

  // Align the wireframe with the hero canvas before first paint
  useIsoLayoutEffect(() => {
    if (done) return
    const canvas = document.querySelector<HTMLElement>('.hero__canvas')
    const svg = svgRef.current
    if (!svg) return
    if (canvas) {
      const r = canvas.getBoundingClientRect()
      Object.assign(svg.style, { left: `${r.left}px`, top: `${r.top}px`, width: `${r.width}px`, height: `${r.height}px` })
    } else {
      Object.assign(svg.style, { left: '8%', top: '12%', width: '84%', height: '60%' })
    }
  }, [done])

  useIsoLayoutEffect(() => {
    const el = ref.current
    if (!el || done) return

    const finish = () => {
      document.documentElement.classList.remove('is-loading')
      markAppReady()
      setDone(true)
    }
    if (prefersReducedMotion()) { finish(); return }

    const ctx = gsap.context(() => {
      const pct = el.querySelector<HTMLElement>('.pl__pct')!
      const paths = gsap.utils.toArray<SVGPathElement>('.pl__wire path')
      const lines = gsap.utils.toArray<HTMLElement>('[data-type]')
      const progress = { v: 0 }
      const guideTravel = () => svgRef.current!.getBoundingClientRect().height

      gsap.set(paths, { strokeDasharray: 1, strokeDashoffset: 1 })
      gsap.set(lines, { autoAlpha: 0 })
      gsap.set('.pl__title .pl__ln > span', TEXT_FROM)

      // Two-phase progress curve: quick to 60%, then eases into 100%
      const LOAD = 5.5
      const tl = gsap.timeline({ onComplete: finish })
      tl.to('.pl__title .pl__ln > span', { ...TEXT_TO, stagger: 0.06 }, 0.1)
        .to(progress, {
          keyframes: [
            { v: 60, duration: 3, ease: 'power2.out' },
            { v: 100, duration: 2.5, ease: 'power3.out' },
          ],
          onUpdate: () => {
            pct.textContent = `${Math.round(progress.v)}%`
            gsap.set('.pl__scan', { scaleX: progress.v / 100 })
          },
        }, 0)
        // Wireframe traces along with the scan
        .to(paths, { strokeDashoffset: 0, duration: DUR, ease: EASE, stagger: { amount: LOAD - 1.2 } }, 0.2)
        // Spec sheet and boot log lines fade in one after another
        .to(lines, { autoAlpha: 1, duration: 0.25, ease: 'power3.out', stagger: 0.3 }, 0.4)

      // Scan line splits into two guides that frame the building
      const T = LOAD + 0.1
      tl.to('.pl__pct', { autoAlpha: 0, duration: 0.2 }, T)
        .set('.pl__scan', { autoAlpha: 0 }, T)
        .set('.pl__guide', { autoAlpha: 1 }, T)
        .to('.pl__guide--top', { y: () => -guideTravel() * 0.42, duration: DUR, ease: EASE_IN_OUT }, T)
        .to('.pl__guide--bot', { y: () => guideTravel() * 0.36, duration: DUR, ease: EASE_IN_OUT }, T)
        // Copy leaves, paper dissolves, hero takes over underneath
        .to('.pl__title .pl__ln > span', { yPercent: -100, autoAlpha: 0, duration: 0.5, ease: 'power2.in', stagger: STAGGER_TEXT }, T + 0.5)
        .to('.pl__meta', { autoAlpha: 0, duration: 0.4, ease: EASE }, T + 0.5)
        .to('.pl__guide', { scaleX: 0, transformOrigin: 'right', duration: DUR, ease: EASE_IN_OUT, stagger: 0.06 }, T + 0.8)
        .to(el, { backgroundColor: 'rgba(243,242,238,0)', duration: 0.6, ease: EASE }, T + 0.9)
        .call(() => { document.documentElement.classList.remove('is-loading'); markAppReady() }, [], T + 0.9)
        .to('.pl__wire', { autoAlpha: 0, duration: DUR, ease: EASE }, T + 1.3)
    }, el)

    return () => ctx.revert()
  }, [])

  if (done) return null
  return (
    <div className="pl" ref={ref} aria-hidden="true">
      <svg className="pl__wire" ref={svgRef} viewBox={VIEWBOX} preserveAspectRatio="xMidYMid meet">
        {PATHS.map((d, i) => <path d={d} key={i} pathLength={1} />)}
      </svg>

      <div className="pl__scanwrap">
        <span className="pl__pct mono">0%</span>
        <span className="pl__scan" />
        <span className="pl__guide pl__guide--top" />
        <span className="pl__guide pl__guide--bot" />
      </div>

      <p className="pl__title h4">
        {preloader.title.map((l) => (
          <span className="pl__ln" key={l}><span>{l}</span></span>
        ))}
      </p>

      <div className="pl__meta mono">
        <dl className="pl__spec">
          <dt className="pl__spec-head" data-type>{preloader.specHead}</dt>
          <dd className="pl__rule" />
          {SPEC.map(([k, v]) => (
            <div className="pl__row" key={k}>
              <dt data-type>{k}</dt>
              <dd data-type>{v}</dd>
            </div>
          ))}
        </dl>
        <ol className="pl__log">
          {LOG.map((l, i) => <li key={l} data-type>{`${String(i + 1).padStart(3, '0')} ${l}`}</li>)}
        </ol>
      </div>
    </div>
  )
}
