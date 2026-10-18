import { useRef, useState } from 'react'
import { SplitText } from '~/components/ui/SplitText'
import { InfoBox } from '~/components/ui/InfoBox'
import { Button } from '~/components/ui/Button'
import { Ruler } from '~/components/ui/Ruler'
import { review } from '~/content/site'
import { gsap } from '~/lib/gsap'
import { useGsap } from '~/hooks/useGsap'
import { useSectionReveal } from '~/hooks/useSplitReveal'

type Wall = [number, number, number, number] // x, y, w, h
// Plan in a 600 × 520 drawing space; openings are simply gaps between wall rects
const WALLS: Wall[] = [
  [60, 60, 180, 14], [280, 60, 260, 14], [526, 60, 14, 170], [526, 270, 14, 190],
  [60, 446, 120, 14], [220, 446, 320, 14], [60, 60, 14, 120], [60, 220, 14, 240],
  [74, 200, 120, 10], [234, 200, 160, 10], [384, 74, 10, 126],
  [300, 210, 10, 110], [300, 360, 10, 86], [394, 300, 132, 10],
]
const DIMS: { x1: number; y1: number; x2: number; y2: number; label: string; vertical?: boolean }[] = [
  { x1: 60, y1: 34, x2: 384, y2: 34, label: '6 480' },
  { x1: 384, y1: 34, x2: 540, y2: 34, label: '3 120' },
  { x1: 572, y1: 60, x2: 572, y2: 300, label: '4 800', vertical: true },
  { x1: 572, y1: 300, x2: 572, y2: 460, label: '3 200', vertical: true },
  { x1: 60, y1: 488, x2: 300, y2: 488, label: '4 800' },
  { x1: 300, y1: 488, x2: 540, y2: 488, label: '4 800' },
]
const VIOLATIONS = review.violations
// Icons pair with review.features by index
const FEATURE_ICONS = [
  'M4 4h16v16H4zM4 9h16M9 9v11',
  'M12 3l8 4.5v9L12 21l-8-4.5v-9zM12 12l8-4.5M12 12v9M12 12 4 7.5',
  'M5 19l4-1 10-10-3-3L6 15zM14 6l3 3',
  'M5 12l4 4 10-10',
]

export function Review() {
  const ref = useRef<HTMLElement>(null)
  const [active, setActive] = useState<number | null>(null)
  const [fixed, setFixed] = useState<Set<number>>(new Set())
  useSectionReveal(ref)

  useGsap(ref, ({ reduced, el }) => {
    if (reduced) return
    const tl = gsap.timeline({ scrollTrigger: { trigger: el.querySelector('.review__plan'), start: 'top 70%' } })
    tl.from(el.querySelectorAll('.plan .wall'), { scaleX: 0, scaleY: 0, transformOrigin: 'center', duration: 0.5, ease: 'expo.out', stagger: 0.02 })
      .from(el.querySelectorAll('.plan .dim, .plan .dimtxt, .plan .furn'), { opacity: 0, duration: 0.4 }, '-=0.4')
      .from(el.querySelectorAll('.marker'), { scale: 0, transformOrigin: 'center', duration: 0.4, ease: 'back.out(3)', stagger: 0.08 }, '-=0.2')
  })

  const v = active === null ? null : VIOLATIONS.find((x) => x.n === active)!
  const remaining = VIOLATIONS.length - fixed.size

  return (
    <section className="sec" id="review" ref={ref}>
      <div className="review">
        <div className="review__plan">
          <svg className="plan" viewBox="0 0 600 520" role="group" aria-label="Floor plan with flagged violations">
            {DIMS.map((d, i) => (
              <g key={i}>
                <line className="dim" x1={d.x1} y1={d.y1} x2={d.x2} y2={d.y2} />
                {d.vertical
                  ? <><line className="dim" x1={d.x1 - 5} y1={d.y1} x2={d.x1 + 5} y2={d.y1} /><line className="dim" x1={d.x2 - 5} y1={d.y2} x2={d.x2 + 5} y2={d.y2} /></>
                  : <><line className="dim" x1={d.x1} y1={d.y1 - 5} x2={d.x1} y2={d.y1 + 5} /><line className="dim" x1={d.x2} y1={d.y2 - 5} x2={d.x2} y2={d.y2 + 5} /></>}
                <text className="dimtxt" textAnchor="middle"
                  x={d.vertical ? d.x1 + 12 : (d.x1 + d.x2) / 2} y={d.vertical ? (d.y1 + d.y2) / 2 : d.y1 - 6}
                  transform={d.vertical ? `rotate(90 ${d.x1 + 12} ${(d.y1 + d.y2) / 2})` : undefined}>{d.label}</text>
              </g>
            ))}
            {/* furniture & fixtures */}
            <g className="furn">
              <rect x="100" y="100" width="90" height="60" /><circle cx="145" cy="130" r="14" />
              <rect x="420" y="100" width="80" height="90" /><line x1="420" y1="120" x2="500" y2="120" />
              <rect x="330" y="240" width="40" height="50" /><circle cx="350" cy="380" r="18" /><rect x="320" y="410" width="60" height="22" />
              <rect x="100" y="260" width="140" height="70" /><rect x="110" y="360" width="60" height="60" />
              <rect x="420" y="340" width="90" height="80" />
              <path d="M240 200a40 40 0 0 1 -40 -40M310 360a50 50 0 0 0 50 -50" />
              <path d="M74 180h-14M74 220h-14" />
            </g>
            {review.image
              ? <image href={review.image.src} x="0" y="0" width="600" height="520" preserveAspectRatio="xMidYMid meet" />
              : WALLS.map(([x, y, w, h], i) => <rect className="wall" key={i} x={x} y={y} width={w} height={h} />)}
            {VIOLATIONS.map((m) => (
              <g
                key={m.n}
                className={`marker${active === m.n ? ' is-active' : ''}${fixed.has(m.n) ? ' is-fixed' : ''}`}
                tabIndex={0}
                role="button"
                aria-pressed={active === m.n}
                aria-label={`Violation ${m.n}: ${m.code}${fixed.has(m.n) ? ', fixed' : ''}`}
                onClick={() => setActive(m.n)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setActive(m.n) } }}
              >
                <rect x={m.x - 13} y={m.y - 13} width="26" height="26" />
                <text x={m.x} y={m.y + 3.5} textAnchor="middle">{fixed.has(m.n) ? '✓' : `0${m.n}`}</text>
              </g>
            ))}
          </svg>

          {v && (
            <div className="violation" aria-live="polite">
              <InfoBox title={`0${v.n} · ${v.code}`}>
                <p>{v.text}</p>
                <p className="mono" style={{ margin: '10px 0', color: 'var(--ink)' }}>Proposed: {v.fix}</p>
                {fixed.has(v.n)
                  ? <p className="mono accent">Applied · logged</p>
                  : <Button label="Apply fix" size="sm" icon={null} onClick={() => setFixed((s) => new Set(s).add(v.n))} />}
              </InfoBox>
            </div>
          )}
          <InfoBox title={review.boxTitle} foot={remaining ? review.boxFoot : review.boxFootDone} />
          <Ruler />
        </div>

        <div className="review__side">
          <p className="review__status mono">{review.status(remaining)}</p>
          <div className="review__copy">
            <SplitText className="h3" text={review.title} />
            <p className="body fade-up">{review.body}</p>
          </div>
          <ul className="review__list">
            {review.features.map((t, i) => (
              <li key={t}><p>{t}</p><span><svg viewBox="0 0 24 24" aria-hidden="true"><path d={FEATURE_ICONS[i % FEATURE_ICONS.length]} /></svg></span></li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}
