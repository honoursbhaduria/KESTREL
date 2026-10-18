import { useRef } from 'react'
import { brand } from '~/content/site'
import { createFileRoute } from '@tanstack/react-router'
import { Label } from '~/components/ui/Label'
import { SplitText } from '~/components/ui/SplitText'
import { Cta } from '~/components/sections/Cta'
import { useSectionReveal } from '~/hooks/useSplitReveal'

export const Route = createFileRoute('/about')({
  head: () => ({
    meta: [
      { title: `Studio — ${brand.name}` },
      { name: 'description', content: 'The team behind Kestrel: architects and engineers building a better review loop.' },
    ],
  }),
  component: About,
})

const VALUES = [
  { n: '01', t: 'Practice first', b: 'Every feature starts as a problem someone on the team hit on a live project.' },
  { n: '02', t: 'Explain everything', b: 'A flag without a reason is noise. Kestrel always shows its working.' },
  { n: '03', t: 'You hold the pen', b: 'Nothing changes in your model unless a person approved it.' },
]

function About() {
  const ref = useRef<HTMLDivElement>(null)
  useSectionReveal(ref)
  return (
    <div ref={ref}>
      <section className="sec page">
        <div className="page__hero">
          <Label>Studio</Label>
          <SplitText as="h1" className="h1" text="Drawn by people who've done the drawing" />
          <p className="body fade-up">
            Kestrel is a small team of architects, BIM managers and engineers. We spent years fixing the same
            avoidable issues late at night, so we built the colleague we wished we'd had.
          </p>
        </div>
      </section>
      <section className="sec">
        <div className="values">
          {VALUES.map((v) => (
            <article className="value fade-up" key={v.n}>
              <span className="mono">[{v.n}]</span>
              <h2 className="h5">{v.t}</h2>
              <p className="body">{v.b}</p>
            </article>
          ))}
        </div>
      </section>
      <Cta />
    </div>
  )
}
