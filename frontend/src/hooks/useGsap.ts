import { useLayoutEffect, useEffect, type RefObject } from 'react'
import { gsap, prefersReducedMotion } from '~/lib/gsap'

const useIsoLayoutEffect = typeof window !== 'undefined' ? useLayoutEffect : useEffect

/**
 * Scoped GSAP setup. Everything created inside `setup` is reverted on unmount.
 * `setup` receives a flag telling it whether the user prefers reduced motion.
 */
export function useGsap<T extends HTMLElement>(
  scope: RefObject<T | null>,
  setup: (ctx: { reduced: boolean; el: T }) => void | (() => void),
  deps: unknown[] = [],
) {
  useIsoLayoutEffect(() => {
    const el = scope.current
    if (!el) return
    let cleanup: void | (() => void)
    const ctx = gsap.context(() => {
      cleanup = setup({ reduced: prefersReducedMotion(), el })
    }, el)
    return () => {
      cleanup?.()
      ctx.revert()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}
