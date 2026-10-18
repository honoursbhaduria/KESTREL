import { createFileRoute } from '@tanstack/react-router'
import { brand } from '~/content/site'
import { Label } from '~/components/ui/Label'
import { Legal } from '~/components/ui/Legal'

export const Route = createFileRoute('/terms')({
  head: () => ({ meta: [{ title: `Terms — ${brand.name}` }] }),
  component: Terms,
})

const SECTIONS = [
  { id: 'service', title: 'The service', body: [
    'Kestrel provides software that reviews building models against rule sets and proposes changes. It assists professional judgement; it does not replace it.',
  ] },
  { id: 'responsibility', title: 'Professional responsibility', body: [
    'You remain responsible for your designs and for compliance with the codes that apply to them. Review results are advice, and approved edits are your decision.',
  ] },
  { id: 'accounts', title: 'Accounts and payment', body: [
    'Plans are billed in advance, monthly or yearly. You can cancel at any time; access continues until the end of the paid period.',
  ] },
  { id: 'data', title: 'Your data', body: [
    'You keep all rights to your models and drawings. We process them only to provide the service, as described in the privacy policy.',
  ] },
  { id: 'changes', title: 'Changes to these terms', body: [
    'We will give at least 30 days’ notice by email before material changes take effect.',
  ] },
]

function Terms() {
  return (
    <section className="sec page">
      <div className="page__hero">
        <Label>Legal</Label>
        <h1 className="h2">Terms of service</h1>
        <p className="body">Template text for a fictional company. Have it reviewed before launch.</p>
      </div>
      <Legal sections={SECTIONS} />
    </section>
  )
}
