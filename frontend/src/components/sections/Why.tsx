import { useRef, useState } from 'react'
import { SplitText } from '~/components/ui/SplitText'
import { InfoBox } from '~/components/ui/InfoBox'
import { gsap, ScrollTrigger } from '~/lib/gsap'
import { useGsap } from '~/hooks/useGsap'
import { useSectionReveal } from '~/hooks/useSplitReveal'
import { why } from '~/content/site'

const STEPS = why.steps
// Points on the plan the agent "learns" from
const PTS: [number, number][] = [[100, 60], [230, 60], [300, 130], [380, 180], [40, 120], [40, 260], [180, 210], [250, 210], [250, 280], [330, 300], [200, 330]]

export function Why() {
  const ref = useRef<HTMLElement>(null)
  const [step, setStep] = useState(0)
  useSectionReveal(ref)

  useGsap(ref, ({ el }) => {
    const toStep = (p: number) => setStep(Math.min(STEPS.length - 1, Math.floor(p * STEPS.length)))
    const mm = gsap.matchMedia()
    // Desktop: step follows the scroll position through the body block
    mm.add('(min-width: 900px)', () => {
      ScrollTrigger.create({ trigger: el.querySelector('.why__body'), start: 'top 60%', end: 'bottom 60%', onUpdate: (st) => toStep(st.progress) })
    })
    // Mobile: the body is a tall track with a sticky stage; progress through it drives the step
    mm.add('(max-width: 899px)', () => {
      ScrollTrigger.create({ trigger: el.querySelector('.why__body'), start: 'top top+=64', end: 'bottom bottom', onUpdate: (st) => toStep(st.progress) })
    })
    return () => mm.revert()
  })

  return (
    <section className="sec" id="why" ref={ref}>
      <div className="why__head">
        <div>
          <p className="mono" data-scramble>{why.label}</p>
          <SplitText className="h2" text={why.title} />
        </div>
        <p className="body fade-up">{why.body}</p>
      </div>
      <div className="why__body">
        <div className="why__stage">
        <ol className="why__steps">
          {STEPS.map((s, i) => (
            <li key={s.title} className={`step${i === step ? ' is-active' : ''}`} onMouseEnter={() => setStep(i)}>
              <h3 className="h5">{s.title}</h3>
              <p>{s.body}</p>
              <i aria-hidden="true" />
            </li>
          ))}
        </ol>
        <div className="why__visual" data-step={step} aria-hidden="true">
          <svg viewBox="0 0 420 380">
            <g className="grid">
              {Array.from({ length: 8 }, (_, i) => <line key={`v${i}`} x1={i * 60} y1="0" x2={i * 60} y2="380" />)}
              {Array.from({ length: 7 }, (_, i) => <line key={`h${i}`} x1="0" y1={i * 60} x2="420" y2={i * 60} />)}
            </g>
            <path className="room" d="M40 60H300l80 80v200H40Z M180 60v150H330 M40 210h140 M250 210v130" />
            <path className="room-new" d="M40 60H300l80 80v200H40Z" />
            {step === 0 && <line className="scan" x1="0" y1="190" x2="420" y2="190" />}
            {PTS.slice(1).map(([x, y], i) => <line key={i} className="link" x1={PTS[i][0]} y1={PTS[i][1]} x2={x} y2={y} />)}
            {PTS.map(([x, y], i) => (
              <g className="pt" key={i}>
                <rect x={x - 6} y={y - 6} width="12" height="12" style={{ transitionDelay: `${i * 40}ms` }} />
                <rect className="core" x={x - 2.5} y={y - 2.5} width="5" height="5" style={{ transitionDelay: `${i * 40}ms` }} />
              </g>
            ))}
          </svg>
          <InfoBox title={why.boxTitles[step] ?? STEPS[step].title}>
            <ul className="mono" style={{ display: 'grid', gap: 4 }}>
              {why.boxItems.map((t) => <li key={t}>· {t}</li>)}
            </ul>
          </InfoBox>
        </div>
        <div className="pager why__pager" aria-hidden="true">
          {STEPS.map((s, i) => <button key={s.title} tabIndex={-1} className={i === step ? 'is-on' : ''} />)}
        </div>
        </div>
      </div>
    </section>
  )
}
