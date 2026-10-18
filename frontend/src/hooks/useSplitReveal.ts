import type { RefObject } from 'react'
import { gsap } from '~/lib/gsap'
import { DUR, EASE, TEXT_FROM, TEXT_TO } from '~/lib/motion'
import { whenPageVisible } from '~/lib/ready'
import { useGsap } from './useGsap'

/** Reveals `.split-word` children of `.split` headings and `.fade-up` blocks on scroll. */
export function useSectionReveal<T extends HTMLElement>(scope: RefObject<T | null>) {
  useGsap(scope, ({ reduced, el }) => {
    if (reduced) return
    // Hide now; animate once the page is on screen (after the preloader or a transition cover)
    gsap.set(el.querySelectorAll('.split .split-word > span'), TEXT_FROM)
    let ctx: gsap.Context | undefined
    const off = whenPageVisible(() => { ctx = gsap.context(() => setup(el), el) })
    return () => { off(); ctx?.revert() }
  })
}

function setup(el: HTMLElement) {
  el.querySelectorAll<HTMLElement>('.split').forEach((heading) => {
    gsap.fromTo(heading.querySelectorAll('.split-word > span'), TEXT_FROM, {
      ...TEXT_TO,
      scrollTrigger: { trigger: heading, start: 'top 85%' },
    })
  })
  el.querySelectorAll<HTMLElement>('.fade-up').forEach((node) => {
    gsap.from(node, {
      y: 24,
      autoAlpha: 0,
      duration: DUR,
      ease: EASE,
      scrollTrigger: { trigger: node, start: 'top 90%' },
    })
  })
}
