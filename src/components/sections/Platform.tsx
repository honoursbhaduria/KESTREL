import { useRef } from 'react'
import { SplitText } from '~/components/ui/SplitText'
import { ButtonLink } from '~/components/ui/Button'
import { gsap } from '~/lib/gsap'
import { DUR_BIG, EASE_BIG } from '~/lib/motion'
import { useGsap } from '~/hooks/useGsap'
import { useSectionReveal } from '~/hooks/useSplitReveal'
import { Slot } from '~/components/ui/Slot'
import { brand, platform } from '~/content/site'

function OverlayMock() {
  return (
    <div className="mock">
      <div className="mock__bar mono"><span>{brand.name} · overlay</span><i /></div>
      <div className="mock__chat">
        <p className="mock__msg mock__msg--user">Does corridor C2 meet egress width?</p>
        <p className="mock__msg">No: 1 050 mm clear, 1 100 required. I can shift three partitions 50 mm east. Preview?</p>
        <div className="mock__actions mono"><span>Apply</span><span>Preview</span><span>Skip</span></div>
      </div>
    </div>
  )
}

const ROWS: [string, 'ok' | 'warn' | 'err'][] = [
  ['Stair riser height', 'ok'], ['Landing depth L3', 'warn'], ['Guard height, terrace', 'err'],
  ['Door clear width', 'ok'], ['Ramp slope R1', 'warn'], ['Window sill, bed 2', 'err'],
]
const STATUS = { ok: 'Pass', warn: 'Review', err: 'Fail' }

function ConsoleMock() {
  return (
    <div className="mock">
      <div className="mock__bar mono"><span>Review · Project 0412</span><i /></div>
      <ul className="mock__rows">
        {ROWS.map(([name, s]) => <li key={name}><b className={s} />{name}<em className="mono">{STATUS[s]}</em></li>)}
      </ul>
    </div>
  )
}

const MOCKS = [OverlayMock, ConsoleMock]

export function Platform() {
  const ref = useRef<HTMLElement>(null)
  useSectionReveal(ref)
  useGsap(ref, ({ reduced, el }) => {
    if (reduced) return
    el.querySelectorAll<HTMLElement>('.product').forEach((p) => {
      gsap.timeline({ scrollTrigger: { trigger: p, start: 'top 70%' } })
        .from(p.querySelector('.mock'), { y: 40, opacity: 0, duration: DUR_BIG, ease: EASE_BIG })
        .from(p.querySelectorAll('.mock__rows li, .mock__msg, .mock__actions'), { x: -12, opacity: 0, stagger: 0.1, duration: 0.5 }, '-=0.5')
    })
  })

  return (
    <section className="sec" id="platform" ref={ref}>
      <div className="platform__head">
        <div>
          <p className="mono" style={{ color: 'var(--ink)', marginBottom: 18 }} data-scramble>{platform.label}</p>
          <SplitText className="h2" text={platform.title} />
        </div>
        <ButtonLink href={platform.cta.href} label={platform.cta.label} />
      </div>
      {platform.products.map(({ title, body, image, href }, i) => {
        const Mock = MOCKS[i % MOCKS.length]
        return (
        <article className="product" key={title}>
          <div className="product__art"><Slot image={image}><Mock /></Slot></div>
          <div className="product__body">
            <span className="mono" data-scramble>[0{i + 1}]</span>
            <div>
              <h3 className="h3">{title}</h3>
              <p className="body">{body}</p>
              <a href={href} className="arrow-link mono">Learn more <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M1 7h12M8 2l5 5-5 5" /></svg></a>
            </div>
          </div>
        </article>
        )
      })}
    </section>
  )
}
