import { createFileRoute } from '@tanstack/react-router'
import { ProductHero } from '~/components/product/ProductHero'
import { KeyFeatures } from '~/components/product/KeyFeatures'
import { HowItWorks } from '~/components/product/HowItWorks'
import { Faq, type FaqItem } from '~/components/sections/Faq'
import { Cta } from '~/components/sections/Cta'

export const Route = createFileRoute('/product')({
  head: () => ({
    meta: [
      { title: 'Product — Kestrel' },
      { name: 'description', content: 'The Kestrel overlay assistant: ask about your model, preview fixes, and approve every change.' },
    ],
  }),
  component: Product,
})

const FAQ: FaqItem[] = [
  { q: 'Does Kestrel change my model without asking?',
    a: 'No. Kestrel proposes edits and shows a preview. Nothing in the model changes until a person approves it, and every approved change can be undone.' },
  { q: 'Which codes and standards are supported?',
    a: 'We ship rule sets for common building, fire and accessibility codes, and you can add your own office standards. Coverage varies by region, so ask us about yours.' },
  { q: 'Where does my model data go?',
    a: 'Geometry is processed in a region you choose and is never used to train shared models. Self-hosted deployment is available on the Practice plan.' },
  { q: 'Do I need to change how I model?',
    a: 'No. Kestrel reads the models you already produce. Cleaner layer and naming conventions help it explain itself, but they are not required.' },
  { q: 'Can the whole team share rules and results?',
    a: 'Yes. Rule libraries, reviews and change logs live in the shared review console, so everyone checks against the same standards.' },
]

function Product() {
  return (
    <>
      <ProductHero />
      <KeyFeatures />
      <HowItWorks />
      <Faq items={FAQ} />
      <Cta />
    </>
  )
}
