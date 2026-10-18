import { useEffect, useRef } from 'react'
import { gsap } from '~/lib/gsap'

/** Custom cursor: follows the pointer, grows over links, shows `data-cursor` labels. */
export function Cursor() {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) return
    document.documentElement.classList.add('has-cursor')
    const label = el.querySelector<HTMLElement>('.cursor__label')!
    const xTo = gsap.quickTo(el, 'x', { duration: 0.35, ease: 'power3' })
    const yTo = gsap.quickTo(el, 'y', { duration: 0.35, ease: 'power3' })

    const move = (e: PointerEvent) => {
      xTo(e.clientX)
      yTo(e.clientY)
      const t = e.target as HTMLElement
      el.classList.toggle('is-hidden', !!t.closest('.hero__canvas-wrap'))
      const labelled = t.closest<HTMLElement>('[data-cursor]')
      const interactive = t.closest('a, button, summary, input, label')
      el.classList.toggle('is-hover', !!interactive && !labelled)
      el.classList.toggle('is-label', !!labelled)
      label.textContent = labelled?.dataset.cursor ?? ''
    }
    const onScroll = () => { el.classList.remove('is-label', 'is-hover') }
    const down = () => el.classList.add('is-down')
    const up = () => el.classList.remove('is-down')
    const leave = () => el.classList.add('is-hidden')
    const enter = () => el.classList.remove('is-hidden')

    window.addEventListener('pointermove', move)
    window.addEventListener('pointerdown', down)
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('pointerup', up)
    document.addEventListener('pointerleave', leave)
    document.addEventListener('pointerenter', enter)
    return () => {
      document.documentElement.classList.remove('has-cursor')
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerdown', down)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('pointerup', up)
      document.removeEventListener('pointerleave', leave)
      document.removeEventListener('pointerenter', enter)
    }
  }, [])

  return (
    <div className="cursor" ref={ref} aria-hidden="true">
      <div className="cursor__dot" />
      <div className="cursor__label mono" />
    </div>
  )
}
