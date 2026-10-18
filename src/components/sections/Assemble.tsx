import { useRef, useState } from 'react'
import { SplitText } from '~/components/ui/SplitText'
import { InfoBox } from '~/components/ui/InfoBox'
import { Box, p } from '~/components/ui/Iso'
import { gsap, ScrollTrigger } from '~/lib/gsap'
import { EASE_BIG } from '~/lib/motion'
import { useGsap } from '~/hooks/useGsap'
import { useSectionReveal } from '~/hooks/useSplitReveal'

const STATS = [
  { label: 'Rooms indexed', value: 214, body: 'Spaces, levels and zones are read straight from the model.', d: 'M4 4h16v16H4zM4 12h9V4' },
  { label: 'Routes traced', value: 38, body: 'Corridors, stairs and exits are followed end to end.', d: 'M4 20V9h8V4h8M16 8l4-4' },
  { label: 'Rules checked', value: 1260, body: 'Code clauses and your own office standards, every pass.', d: 'M5 6h14M5 12h14M5 18h9M17 16l2 2 3-4' },
  { label: 'Fixes proposed', value: 9, body: 'Each one previewed, explained and waiting for a yes.', d: 'M5 19l4-1 10-10-3-3L6 15zM14 6l3 3' },
] as const

type Piece = { x: number; y: number; z: number; w: number; d: number; h: number; step: number; floors?: boolean }
// Pieces in build order, each tied to the stat it illustrates
const PIECES: Piece[] = [
  { x: -120, y: -100, z: 0, w: 240, d: 200, h: 6, step: 0 },
  { x: -70, y: -50, z: 6, w: 140, d: 100, h: 34, step: 1, floors: true },
  { x: -70, y: -50, z: 40, w: 140, d: 100, h: 34, step: 1, floors: true },
  { x: -70, y: -50, z: 74, w: 140, d: 100, h: 34, step: 2, floors: true },
  { x: -70, y: -50, z: 108, w: 140, d: 100, h: 34, step: 2, floors: true },
  { x: -50, y: -30, z: 142, w: 100, d: 60, h: 34, step: 2, floors: true },
  { x: -56, y: -36, z: 176, w: 112, d: 72, h: 6, step: 3 },
]
const ROOF = p(40, -30, 182)
const fmt = (n: number) => n.toLocaleString('en-US').replace(/,/g, ' ')

/**
 * Sticky stage: the building assembles piece by piece as you scroll while the
 * counters on the left tick up, one stat per construction phase.
 */
export function Assemble() {
  const ref = useRef<HTMLElement>(null)
  const [step, setStep] = useState(0)
  useSectionReveal(ref)

  useGsap(ref, ({ reduced, el }) => {
    const nums = el.querySelectorAll<HTMLElement>('.stat__num')
    const render = (progress: number) => {
      nums.forEach((n, i) => {
        const t = gsap.utils.clamp(0, 1, progress * STATS.length - i)
        n.textContent = fmt(Math.round(STATS[i].value * t))
      })
      setStep(Math.min(STATS.length - 1, Math.floor(progress * STATS.length)))
    }
    if (reduced) { render(1); return }

    const pieces = gsap.utils.toArray<SVGGElement>(el.querySelectorAll('.asm__piece'))
    const build = (tl: gsap.core.Timeline) => {
      pieces.forEach((pc, i) => {
        const at = PIECES[i].step + (i % 2) * 0.35
        tl.fromTo(pc, { y: -90, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.6, ease: EASE_BIG }, at)
      })
      tl.fromTo(el.querySelectorAll('.asm__flag'), { scale: 0, autoAlpha: 0, transformOrigin: 'center' }, { scale: 1, autoAlpha: 1, duration: 0.3, ease: 'back.out(3)' }, 3.6)
      tl.to({}, { duration: 0.4 }) // hold the finished building before release
    }

    const mm = gsap.matchMedia()
    // Desktop: the stage is pinned with CSS sticky; scroll position scrubs the build
    mm.add('(min-width: 900px)', () => {
      const tl = gsap.timeline({ scrollTrigger: { trigger: el, start: 'top top', end: 'bottom bottom', scrub: 0.6, onUpdate: (st) => render(st.progress) } })
      build(tl)
    })
    // Mobile: no pin, the build plays once when the stage comes into view
    mm.add('(max-width: 899px)', () => {
      const tl = gsap.timeline({ paused: true })
      build(tl)
      const prog = { v: 0 }
      tl.to(prog, { v: 1, duration: tl.duration(), ease: 'none', onUpdate: () => render(prog.v) }, 0)
      ScrollTrigger.create({ trigger: el.querySelector('.asm__art'), start: 'top 70%', once: true, onEnter: () => { tl.play() } })
    })
    return () => mm.revert()
  })

  return (
    <section className="asm sec" id="assemble" ref={ref}>
      <div className="asm__sticky">
        <div className="asm__copy">
          <div>
            <p className="mono" data-scramble>Under the hood</p>
            <SplitText className="h2" text="It reads the whole building" />
          </div>
          <ol className="asm__stats">
            {STATS.map((s, i) => (
              <li className={`stat${i <= step ? ' is-on' : ''}`} key={s.label}>
                <span className="stat__ic" aria-hidden="true"><svg viewBox="0 0 24 24"><path d={s.d} /></svg></span>
                <div>
                  <p className="mono">{s.label}</p>
                  <p className="stat__body">{s.body}</p>
                </div>
                <b className="stat__num h4" aria-label={fmt(s.value)}>0</b>
              </li>
            ))}
          </ol>
        </div>
        <div className="asm__art" aria-hidden="true">
          <svg viewBox="-240 -330 480 480">
            <g className="asm__grid">
              {Array.from({ length: 11 }, (_, i) => -200 + i * 40).map((v) => (
                <g key={v}>
                  <line x1={p(v, -200, 0)[0]} y1={p(v, -200, 0)[1]} x2={p(v, 200, 0)[0]} y2={p(v, 200, 0)[1]} />
                  <line x1={p(-200, v, 0)[0]} y1={p(-200, v, 0)[1]} x2={p(200, v, 0)[0]} y2={p(200, v, 0)[1]} />
                </g>
              ))}
            </g>
            {PIECES.map((pc, i) => (
              <g className={`asm__piece${pc.step === step ? ' is-current' : ''}`} key={i}>
                <Box x={pc.x} y={pc.y} z={pc.z} w={pc.w} d={pc.d} h={pc.h} />
                {pc.floors && [1, 2].map((k) => {
                  const z = pc.z + (pc.h * k) / 3
                  const a = p(pc.x, pc.y + pc.d, z), b = p(pc.x + pc.w, pc.y + pc.d, z), c = p(pc.x + pc.w, pc.y, z)
                  return <polyline className="asm__mullion" key={k} points={`${a.join(',')} ${b.join(',')} ${c.join(',')}`} />
                })}
              </g>
            ))}
            <g className="asm__flag">
              <rect x={ROOF[0] - 5} y={ROOF[1] - 5} width="10" height="10" />
              <line x1={ROOF[0]} y1={ROOF[1]} x2={ROOF[0] + 60} y2={ROOF[1] - 50} />
            </g>
          </svg>
          <InfoBox title={['Indexing', 'Tracing', 'Checking', 'Ready'][step]} foot={`Phase 0${step + 1} / 04`} className="asm__info">
            {STATS[step].label}: <b className="accent">{fmt(STATS[step].value)}</b>
          </InfoBox>
        </div>
      </div>
    </section>
  )
}
