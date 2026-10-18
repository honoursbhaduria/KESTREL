import { useRef, useState } from 'react'
import { SplitText } from '~/components/ui/SplitText'
import { ButtonLink } from '~/components/ui/Button'
import { Label } from '~/components/ui/Label'
import { Ruler } from '~/components/ui/Ruler'
import { gsap } from '~/lib/gsap'
import { whenPageVisible } from '~/lib/ready'
import { DUR_BIG, DUR_SLOW, EASE_BIG, EASE_SLOW } from '~/lib/motion'
import { useGsap } from '~/hooks/useGsap'
import { usePerView } from '~/hooks/usePerView'
import { useSectionReveal } from '~/hooks/useSplitReveal'

// Tool categories rather than vendor names: the agent is described as tool-agnostic
const TOOLS = ['BIM authoring', '2D CAD', 'NURBS modelling', 'Visual scripting', 'IFC viewers', 'Common data env.', 'Issue trackers']

const CHAT: { who: 'user' | 'agent'; text: string }[] = [
  { who: 'user', text: 'Why is stair S2 flagged?' },
  { who: 'agent', text: 'Going 240 mm, minimum is 250 mm. Rebalancing to 16 risers fixes it and keeps the landing.' },
  { who: 'user', text: 'Show me first.' },
]

/** Elevation of a stair core, with the flagged flight called out. */
function StairArt() {
  const steps = Array.from({ length: 9 }, (_, i) => i)
  return (
    <svg className="phero__plan" viewBox="0 0 480 360" aria-hidden="true">
      <g className="phero__grid">
        {Array.from({ length: 13 }, (_, i) => <line key={`v${i}`} x1={i * 40} y1="0" x2={i * 40} y2="360" />)}
        {Array.from({ length: 10 }, (_, i) => <line key={`h${i}`} x1="0" y1={i * 40} x2="480" y2={i * 40} />)}
      </g>
      <path className="phero__wall" d="M60 320V60h360v260M60 200h120M300 200h120" />
      <path className="phero__stair" d={steps.map((i) => `M${180 + i * 13.3} ${320 - i * 13.3}h13.3v-13.3`).join('')} />
      <path className="phero__stair" d={steps.map((i) => `M${300 - i * 13.3} ${200 - i * 13.3}h-13.3v-13.3`).join('')} />
      <rect className="phero__hit" x="176" y="196" width="128" height="128" />
      <g className="phero__dim">
        <line x1="180" y1="340" x2="300" y2="340" /><line x1="180" y1="334" x2="180" y2="346" /><line x1="300" y1="334" x2="300" y2="346" />
        <text x="240" y="354" textAnchor="middle">2 160</text>
      </g>
      <rect className="phero__mark" x="292" y="188" width="16" height="16" />
    </svg>
  )
}

export function ProductHero() {
  const ref = useRef<HTMLElement>(null)
  const perView = usePerView(5, 2)
  const max = TOOLS.length - perView
  const [index, setIndex] = useState(0)
  const clamped = Math.min(index, max)
  useSectionReveal(ref)

  useGsap(ref, ({ reduced, el }) => {
    if (reduced) return
    const isMobile = typeof window !== 'undefined' && window.innerWidth <= 899
    const tl = gsap.timeline({ paused: true })
      .fromTo(el.querySelector('.phero__plan'), { scale: 1.06, autoAlpha: 0 }, { scale: 1, autoAlpha: 1, duration: DUR_SLOW, ease: EASE_SLOW })
      .fromTo(el.querySelector('.phero__chat'), { x: isMobile ? 0 : 26, y: isMobile ? 16 : 0, autoAlpha: 0 }, { x: 0, y: 0, autoAlpha: 1, duration: DUR_BIG, ease: EASE_BIG }, 0.3)
      .fromTo(el.querySelectorAll('.phero__chat .mock__msg, .phero__chat .mock__actions'), { y: 10, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.5, stagger: 0.25 }, 0.7)
      .fromTo(el.querySelectorAll('.phero__tools > *'), { y: 26, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: DUR_BIG, ease: EASE_BIG, stagger: 0.06 }, 0.2)
    return whenPageVisible(() => tl.play())
  })

  return (
    <section className="phero sec" ref={ref}>
      <div className="phero__grid-wrap">
        <div className="phero__copy">
          <Label>Overlay assistant</Label>
          <SplitText as="h1" className="h1" text="A review panel that floats over your model" />
          <p className="body fade-up">
            Ask about anything on screen, get an answer with the clause attached, and approve the fix without
            switching windows. Kestrel only edits what you say yes to.
          </p>
          <div className="phero__ctas fade-up">
            <ButtonLink href="/#contact" label="Book a walkthrough" />
            <ButtonLink href="/pricing" label="See pricing" variant="ghost" />
          </div>
        </div>
        <div className="phero__art">
          <StairArt />
          <div className="mock phero__chat">
            <div className="mock__bar mono"><span>Kestrel · overlay</span><i /></div>
            <div className="mock__chat">
              {CHAT.map((m) => <p className={`mock__msg${m.who === 'user' ? ' mock__msg--user' : ''}`} key={m.text}>{m.text}</p>)}
              <div className="mock__actions mono"><span>Preview</span><span>Apply</span><span>Skip</span></div>
            </div>
          </div>
        </div>
      </div>
      <Ruler />
      <div className="phero__tools">
        <div className="partners__bar">
          <p className="mono" data-scramble>Works alongside</p>
          <button className="partners__btn" aria-label="Previous tools" disabled={clamped === 0} onClick={() => setIndex(Math.max(0, clamped - 1))}>
            <svg viewBox="0 0 14 14"><path d="M13 7H1M6 2 1 7l5 5" /></svg>
          </button>
          <button className="partners__btn" aria-label="Next tools" disabled={clamped === max} onClick={() => setIndex(Math.min(max, clamped + 1))}>
            <svg viewBox="0 0 14 14"><path d="M1 7h12M8 2l5 5-5 5" /></svg>
          </button>
        </div>
        <div className="partners__viewport">
          <ul className="partners__track" style={{ transform: `translateX(-${clamped * (100 / perView)}%)` }}>
            {TOOLS.map((t) => (
              <li className="partner" key={t}>
                <b><svg viewBox="0 0 18 18" aria-hidden="true"><path d="M3 3h12v12H3zM3 9h12" /></svg>{t}</b>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}
