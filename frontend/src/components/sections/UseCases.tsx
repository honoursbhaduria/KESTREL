import { useRef, useState } from 'react'
import { SplitText } from '~/components/ui/SplitText'
import { Iso } from '~/components/ui/Iso'
import { Slot } from '~/components/ui/Slot'
import { useCases } from '~/content/site'
import { useSectionReveal } from '~/hooks/useSplitReveal'

const CASES = useCases.items

export function UseCases() {
  const ref = useRef<HTMLElement>(null)
  const [open, setOpen] = useState(0)
  useSectionReveal(ref)

  return (
    <section className="sec" id="usecases" ref={ref}>
      <div className="uc">
        <div className="uc__left">
          <div>
            <p className="mono" style={{ marginBottom: 18 }} data-scramble>{useCases.label}</p>
            <SplitText className="h2" text={useCases.title} />
          </div>
          <div>
            {CASES.map((c, i) => {
              const isOpen = open === i
              return (
                <div className={`acc${isOpen ? ' is-open' : ''}`} key={c.title}>
                  <h3>
                    <button className="acc__trigger" aria-expanded={isOpen} aria-controls={`acc-${i}`} id={`acc-btn-${i}`} onClick={() => setOpen(i)}>
                      <span className="h5">{c.title}</span>
                      <span className="acc__icon" aria-hidden="true" />
                    </button>
                  </h3>
                  <div className="acc__panel" id={`acc-${i}`} role="region" aria-labelledby={`acc-btn-${i}`} hidden={!isOpen}>
                    <p className="body">{c.body}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
        <div className="uc__art" aria-hidden="true">
          {CASES.map((c, i) => (
            <div className={`uart${open === i ? ' is-active' : ''}`} key={c.title}>
              <Slot image={c.image}><Iso kind={c.icon} /></Slot>
              <span className="uart__tag mono">{c.title}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
