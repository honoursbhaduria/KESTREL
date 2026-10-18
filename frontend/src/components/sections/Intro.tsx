import { useRef, useState } from 'react'
import { SplitText } from '~/components/ui/SplitText'
import { ButtonLink } from '~/components/ui/Button'
import { AxoScene } from '~/components/ui/Iso'
import { Slot } from '~/components/ui/Slot'
import { intro } from '~/content/site'
import { gsap } from '~/lib/gsap'
import { DUR_BIG, EASE_BIG } from '~/lib/motion'
import { useGsap } from '~/hooks/useGsap'
import { useSectionReveal } from '~/hooks/useSplitReveal'
import { usePerView } from '~/hooks/usePerView'

const PARTNERS = intro.partners

export function Intro() {
  const ref = useRef<HTMLElement>(null)
  const perView = usePerView()
  const max = PARTNERS.length - perView
  const [index, setIndex] = useState(0)
  const clamped = Math.min(index, max)
  useSectionReveal(ref)

  useGsap(ref, ({ reduced, el }) => {
    if (reduced) return
    // Words darken from ghost to ink as the statement scrolls through the viewport
    gsap.fromTo(el.querySelectorAll('.intro__word'), { color: '#b4b4b0' }, {
      color: '#282828', ease: 'none', stagger: 0.1,
      scrollTrigger: { trigger: el.querySelector('.intro__lead'), start: 'top 80%', end: 'bottom 40%', scrub: true },
    })
    gsap.from(el.querySelectorAll('.axo-block'), {
      y: 40, opacity: 0, duration: DUR_BIG, ease: EASE_BIG, stagger: 0.06,
      scrollTrigger: { trigger: el.querySelector('.intro__art'), start: 'top 75%' },
    })
  })

  return (
    <section className="intro sec" id="intro" ref={ref}>
      <div className="intro__lead">
        <h2 className="h3" aria-label={intro.lead}>
          {intro.lead.split(' ').map((w, i) => <span className="intro__word" aria-hidden="true" key={i}>{w} </span>)}
        </h2>
        <ButtonLink href={intro.leadCta.href} label={intro.leadCta.label} variant="ghost" />
      </div>

      <div className="intro__top">
        <div className="intro__art"><Slot image={intro.image}><AxoScene /></Slot></div>
        <div className="intro__partners">
          <div className="partners__bar">
            <p className="mono" data-scramble>{intro.partnersLabel}</p>
            <button className="partners__btn" aria-label="Previous practices" disabled={clamped === 0} onClick={() => setIndex(Math.max(0, clamped - 1))}>
              <svg viewBox="0 0 14 14"><path d="M13 7H1M6 2 1 7l5 5" /></svg>
            </button>
            <button className="partners__btn" aria-label="Next practices" disabled={clamped === max} onClick={() => setIndex(Math.min(max, clamped + 1))}>
              <svg viewBox="0 0 14 14"><path d="M1 7h12M8 2l5 5-5 5" /></svg>
            </button>
          </div>
          <div className="partners__viewport">
            <ul className="partners__track" style={{ transform: `translateX(-${clamped * (100 / perView)}%)` }}>
              {PARTNERS.map((p) => (
                <li className="partner" key={p.name}>
                  {p.logo
                    ? <img src={p.logo} alt={p.name} className="partner__logo" loading="lazy" />
                    : <b><svg viewBox="0 0 18 18" aria-hidden="true"><path d="M2 16 9 2l7 14Z" /></svg>{p.name}</b>}
                </li>
              ))}
            </ul>
          </div>
          <p className="partners__caption mono" data-scramble>{intro.partnersCaption}</p>
        </div>
      </div>

      <div className="intro__statement">
        <div>
          <p className="mono" data-scramble>{intro.label}</p>
          <SplitText className="h2" text={intro.title} />
        </div>
        <p className="body fade-up">{intro.body}</p>
      </div>
    </section>
  )
}
