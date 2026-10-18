import { MASK_DUR, MASK_STEPS } from '~/lib/motion'

const GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#/_-+'

/**
 * Decodes an element's text from random glyphs to its final value, left to right,
 * in discrete steps (same cadence as the stepped button fill).
 * The final text is restored exactly, so it is safe on React-rendered leaf nodes.
 */
export function scramble(el: HTMLElement, duration = MASK_DUR * 1000, steps = MASK_STEPS) {
  const final = el.dataset.scrambleText ?? el.textContent ?? ''
  el.dataset.scrambleText = final
  const start = performance.now()
  let raf = 0
  let lastStep = -1
  const frame = (now: number) => {
    const step = Math.min(steps, Math.floor(((now - start) / duration) * steps))
    if (step !== lastStep) {
      lastStep = step
      const solved = Math.floor((final.length * step) / steps)
      let out = final.slice(0, solved)
      for (let i = solved; i < final.length; i++) {
        out += final[i] === ' ' ? ' ' : GLYPHS[(Math.random() * GLYPHS.length) | 0]
      }
      el.textContent = out
    }
    if (step < steps) raf = requestAnimationFrame(frame)
  }
  raf = requestAnimationFrame(frame)
  return () => { cancelAnimationFrame(raf); el.textContent = final }
}
