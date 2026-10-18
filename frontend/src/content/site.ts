/**
 * All site copy, links and image slots live here.
 *
 * To rebrand: replace the strings below and, for any `image` slot, drop a file into
 * public/assets/ and set the path (e.g. '/assets/hero.webp'). When a slot is left
 * undefined the built-in procedural artwork is used instead.
 *
 * Only put material here that you own or are licensed to use.
 */

export type Link = { label: string; href: string }
export type NavItem = Link | { label: string; children: Link[] }
/** Image slot: a path under /public, plus alt text. Undefined → procedural fallback art. */
export type Img = { src: string; alt: string } | undefined

export const brand = {
  name: 'Kestrel',
  /** Optional logo file under /public (SVG recommended). Undefined → built-in mark. */
  logo: undefined as Img,
  tagline: 'A review agent that lives in your model',
  email: 'hello@kestrel.example',
  copyright: 'Kestrel Labs. All rights reserved.',
}

export const meta = {
  title: 'Kestrel — The design-review agent for architects',
  description:
    'Kestrel is an AI agent that sits inside your modelling software, catches problems as you draw, and fixes them when you say yes.',
}

export const nav: NavItem[] = [
  { label: 'Product', children: [{ label: 'Overlay assistant', href: '/#platform' }, { label: 'Review console', href: '/#platform' }] },
  { label: 'How it works', href: '/#why' },
  { label: 'Who it’s for', children: [{ label: 'Architects', href: '/#usecases' }, { label: 'Interiors', href: '/#usecases' }, { label: 'Landscape', href: '/#usecases' }] },
  { label: 'Studio', href: '/about' },
]
export const navCta: Link = { label: 'Contact', href: '/#contact' }

export const preloader = {
  title: ['Drawn line by line,', 'checked rule', 'by rule.'],
  specHead: 'Welcome to Kestrel',
  spec: [
    ['Type', 'Design-review agent'],
    ['Release', 'Private beta'],
    ['Scope', 'Code & standards checks\ninside BIM / CAD models'],
    ['Studio', 'Remote · Melbourne / Lisbon'],
  ] as [string, string][],
  log: ['Mount drawing set', 'Index rooms & routes', 'Load rule library', 'Resolve dimensions', 'Map annotations', 'Agent ready'],
}

export const hero = {
  title: 'A second pair of eyes inside your model',
  description:
    'Kestrel reads your drawings while you work, flags what a reviewer would send back, and makes the fix the moment you approve it.',
  discover: { label: 'Discover', href: '#intro' },
  /** Image replaces the procedural elevation; issue markers keep working on top of it. */
  image: undefined as Img,
  hint: 'Hold and drag to scan for issues',
  hintDone: 'All issues found',
  /** Marker positions are in drawing units (1000 × 520 box, origin top-left). */
  issues: [
    { id: 'a', x: 612, y: 118, code: 'GRD-02', text: 'Roof terrace guard is 900 mm, needs 1 000 mm' },
    { id: 'b', x: 300, y: 430, code: 'STR-11', text: 'Stair has no handrail on the open side' },
    { id: 'c', x: 742, y: 300, code: 'WIN-05', text: 'Sill height 650 mm above floor without protection' },
    { id: 'd', x: 470, y: 452, code: 'ACC-07', text: 'Entry threshold step of 40 mm on accessible route' },
  ],
  ticker: ['Fewer redlines', 'Less busywork', 'Faster sign-off', 'Clearer handover', 'Rules in context'],
}

export const intro = {
  lead: 'Drafting chores shouldn’t eat the afternoon. Kestrel takes the tedious checks off your plate so your attention stays on the building, not the buttons.',
  leadCta: { label: 'Learn more', href: '#review' },
  image: undefined as Img,
  partnersLabel: 'Practices',
  /** Partner names, or logo images under /public. */
  partners: [
    { name: 'Ostra Studio' }, { name: 'Field & Fold' }, { name: 'Northline' }, { name: 'Atelier Vau' },
    { name: 'Basalt' }, { name: 'Common Ground' }, { name: 'Hale Works' }, { name: 'Ridgeway' },
  ] as { name: string; logo?: string }[],
  partnersCaption: 'Runs inside the BIM, CAD and NURBS tools your team already uses.',
  label: 'The gap',
  title: 'Your software waits. It never warns.',
  body: 'Modelling tools are precise and powerful, but passive. They never suggest, never check, never pick up the slack, so every repetitive step lands back on you.',
}

export type IsoKind = 'hand' | 'gap' | 'blind' | 'pile' | 'tower' | 'room' | 'terrain' | 'grid'

export const problems: { tag: string; title: string; body: string; icon: IsoKind; image?: Img }[] = [
  { tag: 'Manual', icon: 'hand', title: 'Every edit is by hand', body: 'Door swings, dimensions, tags: each one is touched individually, sheet after sheet.' },
  { tag: 'Detached', icon: 'gap', title: 'Help lives in another window', body: 'General chat tools can’t see your model, so you copy, paste and re-explain context all day.' },
  { tag: 'Unseen', icon: 'blind', title: 'Problems hide until review', body: 'A short guard or a tight corridor stays silent in the model until someone else finds it.' },
  { tag: 'Slow', icon: 'pile', title: 'Small jobs eat whole days', body: 'The fiddly upkeep that fills a week is exactly the work software ought to absorb.' },
]

export const statement = {
  lines: ['Beside you', 'From sketch to final set'],
  boxTitle: 'Introduction',
  boxBody: 'Practices lose hours to modelling chores and coordination fixes that pull focus from the design itself.',
  boxFoot: 'Scroll to continue',
}

export const review = {
  status: (open: number) => (open ? `Connected. ${open} open issue${open > 1 ? 's' : ''}` : 'Connected. Model clear'),
  title: 'An agent that runs inside your model',
  body: 'Kestrel sits within the software you already use. It reads the model, understands what you’re working on, and proposes changes you can accept, tweak or ignore. Nothing moves without a yes.',
  /** Replaces the SVG plan; markers stay positioned in the 600 × 520 plan box. */
  image: undefined as Img,
  boxTitle: 'Live review',
  boxFoot: 'Click a violation',
  boxFootDone: 'All clear',
  violations: [
    { n: 1, x: 214, y: 205, code: 'EGR-04', text: 'Opening between hall and living is 820 mm; route needs 900 mm clear.', fix: 'Widen opening to 920 mm' },
    { n: 2, x: 305, y: 340, code: 'ACC-07', text: 'Bathroom door swings into the 1 500 mm turning circle.', fix: 'Re-hang door to swing outward' },
    { n: 3, x: 533, y: 250, code: 'FIR-03', text: 'Bedroom 2 egress window sill sits 1 250 mm above floor.', fix: 'Lower sill to 1 100 mm' },
  ],
  features: [
    'Works inside your BIM and CAD tools.',
    'Understands geometry and intent.',
    'Suggests fixes while you draw.',
    'Edits only after you approve.',
  ],
}

export const platform = {
  label: 'Product',
  title: 'Two ways to work with it',
  cta: { label: 'Book a walkthrough', href: '#contact' },
  products: [
    { title: 'Overlay assistant', image: undefined as Img, href: '#contact',
      body: 'A compact panel that floats over your modelling app. Ask about anything in view or describe a change, and Kestrel carries it out once you confirm.' },
    { title: 'Review console', image: undefined as Img, href: '#contact',
      body: 'A browser workspace for the whole team. Run a full pass over a project, see every flag in context, and ask plain-language questions about requirements.' },
  ],
}

export const why = {
  label: 'Approach',
  title: 'Fits your process. Doesn’t replace it.',
  body: 'Kestrel keeps quiet until something matters, explains itself when it speaks, and never changes a line without your go-ahead, so control stays with you.',
  steps: [
    { title: 'Observe', body: 'Follows the model as you draw: rooms, routes and assemblies.' },
    { title: 'Flag', body: 'Marks conflicts the moment they appear, with the rule attached.' },
    { title: 'Propose', body: 'Suggests fixes and previews the knock-on effects first.' },
    { title: 'Apply', body: 'Edits on approval. Every change is logged and reversible.' },
  ],
  boxTitles: ['Observing…', 'Flagged', 'Proposal', 'Applied'],
  boxItems: ['Layer structure', 'Door / window rules', 'Annotation style', 'Dimensions'],
}

export const useCases = {
  label: 'Use cases',
  title: 'For the people who draw the building',
  items: [
    { title: 'Architects', icon: 'tower' as IsoKind, image: undefined as Img, body: 'Offload the repetitive modelling and code-checking so design time stays design time.' },
    { title: 'Interior designers', icon: 'room' as IsoKind, image: undefined as Img, body: 'Quick answers on clearances, fixture layouts and accessible routes without leaving the model.' },
    { title: 'Landscape architects', icon: 'terrain' as IsoKind, image: undefined as Img, body: 'Keep grading, paths and site furniture aligned with the rules while the scheme is still moving.' },
    { title: 'Technical leads', icon: 'grid' as IsoKind, image: undefined as Img, body: 'Run consistent review passes across every project and spot where the team keeps tripping up.' },
  ],
}

export const cta = {
  title: 'See it work on one of your own drawings',
  body: 'Book a 30-minute walkthrough and we’ll run Kestrel live on a project you choose.',
  placeholder: 'you@studio.com',
  button: 'Request a slot',
  error: 'Please enter a valid work email.',
  success: 'Thanks — we’ll reply within one working day.',
  image: undefined as Img,
}

export const footer = {
  columns: [
    { title: 'Company', links: [{ label: 'Home', href: '/' }, { label: 'Studio', href: '/about' }, { label: 'Contact', href: '/#contact' }] },
    { title: 'Product', links: [{ label: 'Overlay assistant', href: '/#platform' }, { label: 'Review console', href: '/#platform' }, { label: 'How it works', href: '/#why' }] },
    { title: 'Resources', links: [{ label: 'Use cases', href: '/#usecases' }, { label: 'Live demo', href: '/#review' }, { label: 'Careers', href: '/about' }] },
  ],
  subscribeTitle: 'Subscribe',
  subscribeBody: 'Product notes, roughly once a month. No spam.',
  subscribeDone: 'Thanks — you’re on the list.',
  location: { title: 'Studio', lines: ['Remote-first', 'Melbourne · Lisbon'] },
  contactTitle: 'Get in touch',
  social: [{ label: 'LinkedIn', href: '#' }, { label: 'YouTube', href: '#' }, { label: 'Instagram', href: '#' }, { label: 'X', href: '#' }],
  legal: [{ label: 'Privacy policy', href: '/privacy' }, { label: 'Terms', href: '/terms' }, { label: 'Cookies', href: '/privacy#cookies' }],
  /** Large outlined wordmark at the bottom. */
  wordmark: 'KESTREL',
}

export const cookie = { text: 'This site uses a few cookies to see what’s working.', more: 'Learn more', accept: 'Accept', reject: 'Reject' }
