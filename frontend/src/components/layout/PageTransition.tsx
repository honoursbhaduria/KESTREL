import { useEffect, useRef } from 'react'
import { useRouter } from '@tanstack/react-router'
import { gsap, ScrollTrigger, prefersReducedMotion } from '~/lib/gsap'
import { EASE, EASE_IN_OUT } from '~/lib/motion'
import { isAppReady, setTransitioning } from '~/lib/ready'
import { scramble } from '~/lib/scramble'
import { useLenis } from './SmoothScroll'

const COLS = 5
const LABELS: Record<string, string> = { '/': 'Home', '/product': 'Product', '/pricing': 'Pricing', '/about': 'Studio', '/privacy': 'Privacy', '/terms': 'Terms' }
const labelFor = (path: string) => LABELS[path] ?? 'Sheet'

/**
 * Barba-style leave → swap → enter transitions on top of TanStack Router.
 *
 * Internal link clicks are intercepted: the cover drops in as five sheet columns with a
 * scan line and the destination's name, the router swaps the page underneath, scroll is
 * reset, then the columns lift away. Back/forward navigation gets the enter half only,
 * since popstate can't be delayed.
 */
export function PageTransition() {
  const router = useRouter()
  const lenis = useLenis()
  const ref = useRef<HTMLDivElement>(null)
  const busy = useRef(false)
  const ours = useRef(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const cols = el.querySelectorAll<HTMLElement>('.pt__col')
    const label = el.querySelector<HTMLElement>('.pt__label')!
    const scan = el.querySelector<HTMLElement>('.pt__scan')!

    const leave = (to: string) => {
      label.textContent = labelFor(to)
      delete label.dataset.scrambleText
      return gsap.timeline()
        .set(el, { visibility: 'visible' })
        .fromTo(cols, { scaleY: 0, transformOrigin: 'top' }, { scaleY: 1, duration: 0.6, ease: EASE_IN_OUT, stagger: 0.05 })
        .fromTo(scan, { scaleX: 0 }, { scaleX: 1, duration: 0.6, ease: EASE }, 0.25)
        .fromTo(label, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.2, onStart: () => { scramble(label) } }, 0.35)
    }

    const enter = () =>
      gsap.timeline({ onComplete: () => { gsap.set(el, { visibility: 'hidden' }); setTransitioning(false); ScrollTrigger.refresh() } })
        .to([label, scan], { autoAlpha: 0, duration: 0.25, ease: EASE })
        .to(cols, { scaleY: 0, transformOrigin: 'bottom', duration: 0.6, ease: EASE_IN_OUT, stagger: 0.05 }, 0.1)

    const resetScroll = (hash: string) => {
      const target = hash ? document.getElementById(hash) : null
      if (lenis.current) lenis.current.scrollTo(target ?? 0, { immediate: true, force: true })
      else if (target) target.scrollIntoView()
      else window.scrollTo(0, 0)
    }

    const onClick = async (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
      const a = (e.target as HTMLElement).closest<HTMLAnchorElement>('a[href]')
      if (!a || a.target === '_blank' || a.hasAttribute('download')) return
      const url = new URL(a.href, location.href)
      if (url.origin !== location.origin || url.pathname === location.pathname) return // same page: smooth-scroll handles it
      e.preventDefault()
      if (busy.current) return
      if (!isAppReady() || prefersReducedMotion()) {
        router.navigate({ to: url.pathname, hash: url.hash.slice(1) || undefined })
        return
      }
      busy.current = true
      ours.current = true
      setTransitioning(true)
      lenis.current?.stop()
      await leave(url.pathname)
      await router.navigate({ to: url.pathname, hash: url.hash.slice(1) || undefined })
      await new Promise(requestAnimationFrame)
      lenis.current?.start()
      resetScroll(url.hash.slice(1))
      ScrollTrigger.refresh()
      await enter()
      ours.current = false
      busy.current = false
    }

    // Back / forward: cover instantly, then play the enter half once the new page resolves
    const offBefore = router.subscribe('onBeforeNavigate', (ev) => {
      if (ours.current || !ev.pathChanged || !isAppReady() || prefersReducedMotion()) return
      setTransitioning(true)
      label.textContent = labelFor(ev.toLocation.pathname)
      gsap.set(el, { visibility: 'visible' })
      gsap.set(cols, { scaleY: 1 })
      gsap.set([label, scan], { autoAlpha: 1, scaleX: 1 })
    })
    const offResolved = router.subscribe('onResolved', (ev) => {
      if (ours.current || !ev.pathChanged || !isAppReady() || prefersReducedMotion()) return
      requestAnimationFrame(() => { resetScroll(ev.toLocation.hash); enter() })
    })

    document.addEventListener('click', onClick, true)
    return () => {
      document.removeEventListener('click', onClick, true)
      offBefore()
      offResolved()
    }
  }, [router, lenis])

  return (
    <div className="pt" ref={ref} aria-hidden="true">
      {Array.from({ length: COLS }, (_, i) => <span className="pt__col" key={i} />)}
      <span className="pt__scan" />
      <span className="pt__label mono" />
    </div>
  )
}
