import { useRef, useState } from 'react'
import { Iso } from '~/components/ui/Iso'
import { Slot } from '~/components/ui/Slot'
import { problems } from '~/content/site'
import { gsap } from '~/lib/gsap'
import { DUR, EASE } from '~/lib/motion'
import { useGsap } from '~/hooks/useGsap'

const CARDS = problems

export function Problem() {
  const ref = useRef<HTMLElement>(null)
  const trackRef = useRef<HTMLDivElement>(null)
  const [page, setPage] = useState(0)

  // Mobile carousel: derive the active card from the horizontal scroll position
  const onScroll = () => {
    const t = trackRef.current
    if (!t) return
    const card = t.firstElementChild as HTMLElement | null
    if (card) setPage(Math.round(t.scrollLeft / card.offsetWidth))
  }
  const goTo = (i: number) => {
    const t = trackRef.current
    const card = t?.children[i] as HTMLElement | undefined
    if (t && card) t.scrollTo({ left: card.offsetLeft - t.offsetLeft, behavior: 'smooth' })
  }

  useGsap(ref, ({ reduced, el }) => {
    if (reduced) return
    el.querySelectorAll<HTMLElement>('.card').forEach((card, i) => {
      const tl = gsap.timeline({ scrollTrigger: { trigger: el, start: 'top 70%' }, delay: i * 0.12 })
      tl.from(card.querySelectorAll('.card__icon polygon, .card__icon polyline, .card__icon circle'), {
        opacity: 0, y: -12, duration: DUR, ease: EASE, stagger: 0.03,
      }).from(card.querySelectorAll('.card__body > *'), { y: 24, opacity: 0, duration: DUR, ease: EASE, stagger: 0.08 }, 0.2)
    })
  })

  return (
    <section className="sec" id="problem" ref={ref}>
      <div className="cards" ref={trackRef} onScroll={onScroll}>
        {CARDS.map((c, i) => (
          <article className="card" key={c.tag}>
            <header className="card__head mono"><span data-scramble>{c.tag}</span><span data-scramble>[0{i + 1}]</span></header>
            <div className="card__icon"><Slot image={c.image}><Iso kind={c.icon} /></Slot></div>
            <div className="card__body">
              <h3 className="h5">{c.title}</h3>
              <p className="body">{c.body}</p>
            </div>
          </article>
        ))}
      </div>
      <div className="pager" role="tablist" aria-label="Problem cards">
        {CARDS.map((c, i) => (
          <button key={c.tag} role="tab" aria-selected={page === i} aria-label={`Show card ${i + 1}: ${c.title}`} className={page === i ? 'is-on' : ''} onClick={() => goTo(i)} />
        ))}
      </div>
    </section>
  )
}
