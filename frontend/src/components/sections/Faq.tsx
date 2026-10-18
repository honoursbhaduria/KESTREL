import { useId, useRef, useState } from 'react'
import { SplitText } from '~/components/ui/SplitText'
import { useSectionReveal } from '~/hooks/useSplitReveal'

export type FaqItem = { q: string; a: string }

/** Title cell beside a single-open accordion; shares the `.acc` styles with Use cases. */
export function Faq({ items, title = 'Questions, answered', label = 'FAQ', id = 'faq' }: { items: FaqItem[]; title?: string; label?: string; id?: string }) {
  const ref = useRef<HTMLElement>(null)
  const [open, setOpen] = useState<number | null>(0)
  const uid = useId()
  useSectionReveal(ref)

  return (
    <section className="sec" id={id} ref={ref}>
      <div className="faq">
        <div className="faq__head">
          <p className="mono" data-scramble>{label}</p>
          <SplitText className="h2" text={title} />
          <p className="body fade-up">
            Something else? <a href="/#contact" className="accent">Ask us directly</a> and a person will reply.
          </p>
        </div>
        <div className="faq__list">
          {items.map((item, i) => {
            const isOpen = open === i
            return (
              <div className={`acc${isOpen ? ' is-open' : ''}`} key={item.q}>
                <h3>
                  <button className="acc__trigger" aria-expanded={isOpen} aria-controls={`${uid}-p${i}`} id={`${uid}-b${i}`} onClick={() => setOpen(isOpen ? null : i)}>
                    <span className="faq__n mono">[{String(i + 1).padStart(2, '0')}]</span>
                    <span className="faq__q">{item.q}</span>
                    <span className="acc__icon" aria-hidden="true" />
                  </button>
                </h3>
                <div className="acc__panel" id={`${uid}-p${i}`} role="region" aria-labelledby={`${uid}-b${i}`} hidden={!isOpen}>
                  <p className="body">{item.a}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
