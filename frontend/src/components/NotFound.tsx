import { useRef } from 'react'
import { ButtonLink } from '~/components/ui/Button'
import { gsap } from '~/lib/gsap'
import { TEXT_FROM, TEXT_TO } from '~/lib/motion'
import { useGsap } from '~/hooks/useGsap'

/** 404: a plan view with a missing room, and a dashed outline where it should be. */
export function NotFound() {
  const ref = useRef<HTMLElement>(null)
  useGsap(ref, ({ reduced }) => {
    if (reduced) return
    gsap.fromTo('.nf__digit', TEXT_FROM, { ...TEXT_TO, stagger: 0.06, delay: 0.2 })
    gsap.to('.nf__missing', { strokeDashoffset: -40, repeat: -1, duration: 2, ease: 'none' })
  })

  return (
    <section className="nf sec" ref={ref}>
      <div className="nf__inner">
        <p className="mono accent">Error 404</p>
        <h1 className="nf__code" aria-label="404">
          {'404'.split('').map((d, i) => (
            <span className="nf__mask" key={i} aria-hidden="true"><span className="nf__digit">{d}</span></span>
          ))}
        </h1>
        <svg className="nf__plan" viewBox="0 0 300 160" aria-hidden="true">
          <rect x="10" y="10" width="100" height="140" />
          <rect x="110" y="10" width="80" height="70" />
          <rect className="nf__missing" x="110" y="80" width="80" height="70" />
          <rect x="190" y="10" width="100" height="140" />
          <text x="150" y="120" textAnchor="middle">?</text>
        </svg>
        <p className="body">This room isn't in the model. Kestrel flagged it for you.</p>
        <ButtonLink href="/" label="Back to the plan" />
      </div>
    </section>
  )
}
