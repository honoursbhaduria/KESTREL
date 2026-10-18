import { useRef, useState } from 'react'
import { brand } from '~/content/site'
import { createFileRoute } from '@tanstack/react-router'
import { Label } from '~/components/ui/Label'
import { SplitText } from '~/components/ui/SplitText'
import { ButtonLink } from '~/components/ui/Button'
import { Faq, type FaqItem } from '~/components/sections/Faq'
import { Cta } from '~/components/sections/Cta'
import { useSectionReveal } from '~/hooks/useSplitReveal'

export const Route = createFileRoute('/pricing')({
  head: () => ({
    meta: [
      { title: `Pricing — ${brand.name}` },
      { name: 'description', content: 'Plans for independent architects, studios and larger practices.' },
    ],
  }),
  component: Pricing,
})

type Billing = 'monthly' | 'yearly'
type Plan = { name: string; blurb: string; price: Record<Billing, number> | null; unit: string; features: string[]; cta: string; featured?: boolean }

// Example prices for the fictional product
const PLANS: Plan[] = [
  { name: 'Solo', blurb: 'For independent architects and designers.', price: { monthly: 39, yearly: 32 }, unit: 'per month',
    features: ['Overlay assistant', 'Building code rule sets', '200 reviews a month', 'Email support'], cta: 'Start a trial' },
  { name: 'Studio', blurb: 'For teams sharing standards across projects.', price: { monthly: 79, yearly: 65 }, unit: 'per seat / month', featured: true,
    features: ['Everything in Solo', 'Review console for the team', 'Custom office standards', 'Unlimited reviews', 'Shared change log'], cta: 'Start a trial' },
  { name: 'Practice', blurb: 'For larger offices with their own requirements.', price: null, unit: 'annual agreement',
    features: ['Everything in Studio', 'Self-hosted deployment', 'SSO and audit export', 'Rule-set onboarding', 'Named support lead'], cta: 'Talk to us' },
]

const FAQ: FaqItem[] = [
  { q: 'Is there a free trial?', a: 'Yes. Solo and Studio include 14 days free with full features. No card is needed to start.' },
  { q: 'What counts as a review?', a: 'One full pass of the rule set over a model or a selection. Live flags while you draw are not counted.' },
  { q: 'Can I switch plans later?', a: 'Any time. Upgrades apply immediately; downgrades take effect at the end of the billing period.' },
  { q: 'Do you offer education pricing?', a: 'Students and teaching staff get Solo at no cost. Get in touch with your institution email.' },
]

function Pricing() {
  const ref = useRef<HTMLDivElement>(null)
  const [billing, setBilling] = useState<Billing>('yearly')
  useSectionReveal(ref)

  return (
    <div ref={ref}>
      <section className="sec page">
        <div className="page__hero pricing__hero">
          <div>
            <Label>Pricing</Label>
            <SplitText as="h1" className="h1" text="Priced per seat, not per drawing" />
          </div>
          <div className="billing fade-up" role="group" aria-label="Billing period">
            {(['monthly', 'yearly'] as const).map((b) => (
              <button key={b} className={`billing__opt mono${billing === b ? ' is-on' : ''}`} aria-pressed={billing === b} onClick={() => setBilling(b)}>
                {b === 'monthly' ? 'Monthly' : 'Yearly · save 18%'}
              </button>
            ))}
          </div>
        </div>
      </section>
      <section className="sec">
        <div className="plans">
          {PLANS.map((p, i) => (
            <article className={`plan${p.featured ? ' plan--featured' : ''}`} key={p.name}>
              <header className="plan__head mono"><span>[0{i + 1}]</span><span>{p.featured ? 'Most teams' : ''}</span></header>
              <div className="plan__top">
                <h2 className="h4">{p.name}</h2>
                <p className="body">{p.blurb}</p>
              </div>
              <p className="plan__price">
                {p.price ? <><span className="h2" key={billing}>€{p.price[billing]}</span><span className="mono">{p.unit}</span></>
                  : <><span className="h2">Custom</span><span className="mono">{p.unit}</span></>}
              </p>
              <ul className="plan__features">
                {p.features.map((f) => <li key={f}><svg viewBox="0 0 14 14" aria-hidden="true"><path d="M2 7.5 5.5 11 12 3.5" /></svg>{f}</li>)}
              </ul>
              <ButtonLink href="/#contact" label={p.cta} variant={p.featured ? 'accent' : 'ghost'} className="plan__cta" />
            </article>
          ))}
        </div>
        <p className="plans__note mono">Prices exclude VAT. Yearly plans are billed once a year.</p>
      </section>
      <Faq items={FAQ} title="Billing questions" label="Pricing FAQ" />
      <Cta />
    </div>
  )
}
