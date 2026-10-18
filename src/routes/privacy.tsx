import { createFileRoute } from '@tanstack/react-router'
import { brand } from '~/content/site'
import { Label } from '~/components/ui/Label'
import { Legal } from '~/components/ui/Legal'

export const Route = createFileRoute('/privacy')({
  head: () => ({ meta: [{ title: `Privacy — ${brand.name}` }] }),
  component: Privacy,
})

const SECTIONS = [
  { id: 'collect', title: 'What we collect', body: [
    'Account details you give us: name, work email, company and billing information.',
    'Model data you choose to review. Geometry and metadata are processed to produce review results and are not used to train shared models.',
    'Basic usage data, such as which features are used and error reports, to keep the product working.',
  ] },
  { id: 'use', title: 'How we use it', body: [
    'To run the service, provide support, send product notices you asked for, and meet legal obligations.',
    'We do not sell personal data, and we do not share model data with third parties except the processors that host the service.',
  ] },
  { id: 'cookies', title: 'Cookies', body: [
    'This site uses a small number of cookies. Essential cookies remember choices such as your cookie preference. Analytics cookies, if you accept them, tell us which pages are useful.',
    'You can change your choice at any time by clearing this site’s data in your browser; the cookie notice will then appear again.',
  ] },
  { id: 'rights', title: 'Your rights', body: [
    'You can ask for a copy of your data, ask us to correct or delete it, or object to how it is used. Write to privacy@kestrel.example and we will reply within 30 days.',
  ] },
]

function Privacy() {
  return (
    <section className="sec page">
      <div className="page__hero">
        <Label>Legal</Label>
        <h1 className="h2">Privacy policy</h1>
        <p className="body">Template text for a fictional company. Have it reviewed before launch.</p>
      </div>
      <Legal sections={SECTIONS} />
    </section>
  )
}
