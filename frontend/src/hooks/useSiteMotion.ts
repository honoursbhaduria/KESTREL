import { useEffect } from 'react'
import { useRouterState } from '@tanstack/react-router'
import { gsap, ScrollTrigger, prefersReducedMotion } from '~/lib/gsap'
import { whenPageVisible } from '~/lib/ready'
import { scramble } from '~/lib/scramble'
import { DUR, DUR_BIG, DUR_SLOW, EASE, EASE_BIG, EASE_SLOW, STAGGER_CELL } from '~/lib/motion'

/**
 * Site-wide scroll choreography, re-armed on every route change:
 * - `[data-scramble]` mono labels decode from random glyphs
 * - rulers draw in from the left
 * - grid cells rise in, staggered per batch
 * - illustration panels wipe open with a clip-path
 */
export function useSiteMotion() {
  const path = useRouterState({ select: (s) => s.location.pathname })

  useEffect(() => {
    if (prefersReducedMotion()) return
    let ctx: gsap.Context | undefined
    const stops: (() => void)[] = []

    const off = whenPageVisible(() => {
      // Wait a frame so the new route's DOM is in place
      requestAnimationFrame(() => {
        ctx = gsap.context(() => {
          // Header cells drop in one after another
          gsap.from('.header__logo, .nav__item, .menu-btn', { yPercent: -100, autoAlpha: 0, duration: DUR, ease: EASE, stagger: 0.05, delay: 0.1 })

          ScrollTrigger.batch('[data-scramble]', {
            start: 'top 92%',
            once: true,
            onEnter: (els) => els.forEach((el, i) => setTimeout(() => stops.push(scramble(el as HTMLElement)), i * 60)),
          })

          gsap.utils.toArray<HTMLElement>('main .ruler, .footer .ruler').forEach((r) => {
            if (r.closest('.hero')) return
            gsap.from(r, { scaleX: 0, transformOrigin: 'left', duration: DUR_SLOW, ease: EASE_SLOW, scrollTrigger: { trigger: r, start: 'top 95%' } })
          })

          const cells = '.card, .product__body > div, .review__list li, .step, .fcell, .value, .acc, .partner, .how__step, .plan, .legal__sec'
          gsap.set(cells, { opacity: 0, y: 30 })
          ScrollTrigger.batch(cells, {
            start: 'top 92%',
            once: true,
            onEnter: (els) => gsap.to(els, { opacity: 1, y: 0, duration: DUR, ease: EASE, stagger: STAGGER_CELL, overwrite: true }),
          })

          gsap.utils.toArray<HTMLElement>('.intro__art, .product__art, .uc__art, .why__visual, .phero__art').forEach((el) => {
            gsap.fromTo(el, { clipPath: 'inset(0 0 100% 0)' }, {
              clipPath: 'inset(0 0 0% 0)', duration: DUR_BIG, ease: EASE_BIG,
              scrollTrigger: { trigger: el, start: 'top 85%' },
            })
          })

          // Gentle parallax on illustrations inside their cells
          gsap.utils.toArray<HTMLElement>('.intro__art svg, .card__icon svg, .uart svg').forEach((el) => {
            gsap.fromTo(el, { yPercent: 6 }, { yPercent: -6, ease: 'none', scrollTrigger: { trigger: el, scrub: true } })
          })

          ScrollTrigger.refresh()
        })
      })
    })

    return () => {
      off()
      stops.forEach((s) => s())
      ctx?.revert()
    }
  }, [path])
}
