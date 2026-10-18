/**
 * Motion tokens. Timings measured from the reference site's runtime animation log
 * (see tools/scrape-reference.mjs): most reveals are power2.out over 0.8s with a
 * 0.02s stagger; larger moves use power3 (1s) or expo.out (1.6s).
 */
export const EASE = 'power2.out'
export const EASE_IN_OUT = 'power2.inOut'
export const EASE_BIG = 'power3.out'
export const EASE_SLOW = 'expo.out'

export const DUR = 0.8
export const DUR_BIG = 1
export const DUR_SLOW = 1.6

/** Per-word / per-line stagger for text reveals. */
export const STAGGER_TEXT = 0.02
/** Per-cell stagger for grid items. */
export const STAGGER_CELL = 0.08

/** Text reveal: masked lines/words rise from below while fading in. */
export const TEXT_FROM = { yPercent: 100, autoAlpha: 0 }
export const TEXT_TO = { yPercent: 0, autoAlpha: 1, duration: DUR, ease: EASE, stagger: STAGGER_TEXT }

/** Button fill: stepped mask wipe. */
export const MASK_STEPS = 19
export const MASK_DUR = 0.58
