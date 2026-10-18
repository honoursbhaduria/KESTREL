import { useRef } from 'react'
import { SplitText } from '~/components/ui/SplitText'
import { Iso, type IsoKind } from '~/components/ui/Iso'
import { gsap } from '~/lib/gsap'
import { DUR_BIG, EASE_BIG } from '~/lib/motion'
import { useGsap } from '~/hooks/useGsap'
import { useSectionReveal } from '~/hooks/useSplitReveal'

const STEPS: { title: string; body: string; time: string; icon: IsoKind }[] = [
  { title: 'Install the plug-in', time: '5 min', icon: 'grid',
    body: 'One installer per workstation. Kestrel appears as a panel in your modelling app, nothing else changes.' },
  { title: 'Load your rule sets', time: '1 day', icon: 'pile',
    body: 'Pick the codes that apply, then add office standards. We help import the ones you already keep in documents.' },
  { title: 'Review as you draw', time: 'Ongoing', icon: 'tower',
    body: 'Flags appear while you work. Approve, tweak or dismiss; the team console keeps everyone on the same page.' },
]

export function HowItWorks() {
  const ref = useRef<HTMLElement>(null)
  useSectionReveal(ref)

  useGsap(ref, ({ reduced, el }) => {
    if (reduced) return
    gsap.timeline({ scrollTrigger: { trigger: el.querySelector('.how__steps'), start: 'top 75%' } })
      .from(el.querySelectorAll('.how__line'), { scaleX: 0, transformOrigin: 'left', duration: DUR_BIG, ease: EASE_BIG })
      .from(el.querySelectorAll('.how__icon svg'), { y: 30, autoAlpha: 0, duration: DUR_BIG, ease: EASE_BIG, stagger: 0.12 }, 0.1)
  })

  return (
    <section className="sec" id="how" ref={ref}>
      <div className="how__head">
        <div>
          <p className="mono" data-scramble>How it works</p>
          <SplitText className="h2" text="Running by the end of the week" />
        </div>
        <p className="body fade-up">No migration, no new file format. Kestrel reads the models you already have.</p>
      </div>
      <div className="how__track">
      <span className="how__line" aria-hidden="true" />
      <ol className="how__steps">
        {STEPS.map((s, i) => (
          <li className="how__step" key={s.title}>
            <header className="how__meta mono"><span className="accent">Step 0{i + 1}</span><span>{s.time}</span></header>
            <div className="how__icon"><Iso kind={s.icon} /></div>
            <div className="how__text">
              <h3 className="h5">{s.title}</h3>
              <p className="body">{s.body}</p>
            </div>
          </li>
        ))}
      </ol>
      </div>
    </section>
  )
}
