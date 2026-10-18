import { useRef, useState } from 'react'
import { SplitText } from '~/components/ui/SplitText'
import { gsap, ScrollTrigger } from '~/lib/gsap'
import { useGsap } from '~/hooks/useGsap'
import { useSectionReveal } from '~/hooks/useSplitReveal'

function AskVisual() {
  return (
    <div className="mock">
      <div className="mock__bar mono"><span>Ask · Level 03</span><i /></div>
      <div className="mock__chat">
        <p className="mock__msg mock__msg--user">Which rooms on this level miss daylight targets?</p>
        <p className="mock__msg">Two: Bed 3 (glazing 8.1% of floor area) and Study (7.4%). Target is 10%. Want options for both?</p>
        <div className="mock__actions mono"><span>Show options</span><span>Zoom to</span></div>
      </div>
    </div>
  )
}

function FixVisual() {
  return (
    <div className="mock">
      <div className="mock__bar mono"><span>Preview · ACC-07</span><i /></div>
      <svg className="kf__fix" viewBox="0 0 320 180" aria-hidden="true">
        <path className="kf__wall" d="M20 20h280v140H20zM160 20v60M160 120v40" />
        <path className="kf__ghost" d="M160 80a40 40 0 0 1 40 40" />
        <path className="kf__new" d="M160 120a40 40 0 0 1 -40 -40" />
        <circle className="kf__turn" cx="230" cy="100" r="48" />
        <text x="230" y="104" textAnchor="middle">Ø 1 500</text>
      </svg>
      <ul className="mock__rows">
        <li><b className="err" />Door swing in turning circle<em className="mono">Before</em></li>
        <li><b className="ok" />Swing re-hung outward<em className="mono">After</em></li>
      </ul>
    </div>
  )
}

const RULES: [string, boolean][] = [['Minimum corridor 1 100 mm', true], ['Office: tag every door', true], ['Sill ≥ 1 100 mm on bedrooms', true], ['Client: no glazed balustrades', false]]

function RulesVisual() {
  return (
    <div className="mock">
      <div className="mock__bar mono"><span>Rule library · 4 sets</span><i /></div>
      <ul className="mock__rows">
        {RULES.map(([r, on]) => (
          <li key={r}><b className={on ? 'ok' : 'warn'} />{r}<em className="mono">{on ? 'On' : 'Draft'}</em></li>
        ))}
      </ul>
    </div>
  )
}

const LOG: [string, string][] = [['14:02', 'Widened opening W12 to 920 mm'], ['14:05', 'Re-hung door D8 outward'], ['14:11', 'Lowered sill, bed 2'], ['14:12', 'Undo: sill, bed 2']]

function LogVisual() {
  return (
    <div className="mock">
      <div className="mock__bar mono"><span>Change log · today</span><i /></div>
      <ol className="kf__log">
        {LOG.map(([t, e]) => <li key={t}><span className="mono">{t}</span>{e}</li>)}
      </ol>
    </div>
  )
}

const FEATURES = [
  { id: 'ask', tab: 'Ask', title: 'Ask about anything in view', Visual: AskVisual,
    body: 'Questions are answered against the live model, not a screenshot. Kestrel cites the clause or standard behind every answer.' },
  { id: 'preview', tab: 'Preview', title: 'Fixes, previewed first', Visual: FixVisual,
    body: 'Every proposal shows before and after on the drawing, with the knock-on effects listed, before anything moves.' },
  { id: 'rules', tab: 'Rules', title: 'Your standards, not just the code', Visual: RulesVisual,
    body: 'Load office drawing standards and client briefs next to building regulations. Kestrel checks them all in one pass.' },
  { id: 'log', tab: 'Log', title: 'Every change on the record', Visual: LogVisual,
    body: 'Edits are logged with who approved them and why. Any change can be undone, individually, at any time.' },
]

/** Sticky tab column beside a scrolling feature list; the active tab follows scroll position. */
export function KeyFeatures() {
  const ref = useRef<HTMLElement>(null)
  const [active, setActive] = useState(0)
  useSectionReveal(ref)

  useGsap(ref, ({ reduced, el }) => {
    el.querySelectorAll<HTMLElement>('.kf__item').forEach((item, i) => {
      ScrollTrigger.create({ trigger: item, start: 'top 55%', end: 'bottom 55%', onToggle: (st) => { if (st.isActive) setActive(i) } })
      if (reduced) return
      // Title words brighten in sequence as the item scrolls up, like the reference's scrubbed titles
      gsap.fromTo(item.querySelectorAll('.kf__word'), { opacity: 0.15, y: 14 }, {
        opacity: 1, y: 0, stagger: 0.1, ease: 'none',
        scrollTrigger: { trigger: item, start: 'top 85%', end: 'top 45%', scrub: true },
      })
      gsap.from(item.querySelector('.kf__visual'), { y: 40, autoAlpha: 0, duration: 1, ease: 'power3', scrollTrigger: { trigger: item, start: 'top 70%' } })
    })
  })

  return (
    <section className="sec" id="features" ref={ref}>
      <div className="kf">
        <div className="kf__side">
          <div className="kf__sticky">
            <p className="mono" data-scramble>Key features</p>
            <SplitText className="h2" text="Built for the drawing, not the chat window" />
            <ol className="kf__tabs">
              {FEATURES.map((f, i) => (
                <li key={f.id}>
                  <a href={`#kf-${f.id}`} className={`kf__tab mono${i === active ? ' is-active' : ''}`} aria-current={i === active ? 'step' : undefined}>
                    <span>[0{i + 1}]</span>{f.tab}<i aria-hidden="true" />
                  </a>
                </li>
              ))}
            </ol>
          </div>
        </div>
        <div className="kf__list">
          {FEATURES.map(({ id, title, body, Visual }, i) => (
            <article className="kf__item" id={`kf-${id}`} key={id}>
              <header className="kf__head mono"><span>Feature</span><span>[0{i + 1} / 0{FEATURES.length}]</span></header>
              <h3 className="h3 kf__title" aria-label={title}>
                {title.split(' ').map((w, k) => <span className="kf__word" aria-hidden="true" key={k}>{w} </span>)}
              </h3>
              <p className="body">{body}</p>
              <div className="kf__visual"><Visual /></div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
