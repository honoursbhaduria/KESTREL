import { useRef } from 'react'
import { Ruler } from '~/components/ui/Ruler'
import { InfoBox } from '~/components/ui/InfoBox'
import { statement } from '~/content/site'
import { gsap } from '~/lib/gsap'
import { useGsap } from '~/hooks/useGsap'

const LINES = statement.lines

/** Pinned stage: two big lines hand over to each other as you scroll. */
export function Statement() {
  const ref = useRef<HTMLElement>(null)

  useGsap(ref, ({ reduced, el }) => {
    const lines = el.querySelectorAll<HTMLElement>('.stmt__line')
    if (reduced) { gsap.set(lines[1], { autoAlpha: 0 }); return }
    gsap.set(lines[1], { yPercent: 60, autoAlpha: 0 })
    gsap.timeline({ scrollTrigger: { trigger: el, start: 'top top', end: 'bottom bottom', scrub: 0.6 } })
      .fromTo(lines[0], { scale: 0.92, color: '#282828' }, { scale: 1, duration: 1 })
      .to(lines[0], { yPercent: -60, autoAlpha: 0, duration: 1 })
      .to(lines[1], { yPercent: 0, autoAlpha: 1, duration: 1 }, '<0.2')
      .to(lines[1], { color: '#b4b4b0', duration: 1 })
      .fromTo('.stmt__deco--a', { x: -200 }, { x: 0, duration: 3 }, 0)
      .fromTo('.stmt__deco--b', { x: 200 }, { x: 0, duration: 3 }, 0)
  })

  return (
    <section className="stmt sec" ref={ref} aria-label={LINES.join(', ')}>
      <div className="stmt__sticky">
        <Ruler />
        <div className="stmt__stage">
          <svg className="stmt__deco stmt__deco--a" viewBox="0 0 200 240" aria-hidden="true">
            <path d="M0 100h120v20h20v120M50 0v100" />
          </svg>
          <svg className="stmt__deco stmt__deco--b" viewBox="0 0 140 60" aria-hidden="true">
            <path d="M0 10h140M0 30h140M20 10v20" />
          </svg>
          {LINES.map((l) => <p className="stmt__line h2" aria-hidden="true" key={l}>{l}</p>)}
          <InfoBox title={statement.boxTitle} foot={statement.boxFoot}>{statement.boxBody}</InfoBox>
        </div>
        <Ruler />
      </div>
    </section>
  )
}
