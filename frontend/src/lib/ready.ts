/**
 * Page-visibility signals.
 * - "app ready": fired once, when the preloader hands over (sticky).
 * - "page entered": fired each time a route transition's cover has lifted.
 * `whenPageVisible` runs a callback once the current page is actually on screen.
 */
type Cb = () => void

let ready = false
let transitioning = false
const readyListeners = new Set<Cb>()
const enterListeners = new Set<Cb>()

export function onAppReady(cb: Cb): () => void {
  if (ready) {
    cb()
    return () => {}
  }
  readyListeners.add(cb)
  return () => readyListeners.delete(cb)
}

export function markAppReady() {
  if (ready) return
  ready = true
  readyListeners.forEach((cb) => cb())
  readyListeners.clear()
}

export const isAppReady = () => ready

/** Called by the page transition while its cover is up. */
export function setTransitioning(value: boolean) {
  transitioning = value
  if (!value) {
    const cbs = [...enterListeners]
    enterListeners.clear()
    cbs.forEach((cb) => cb())
  }
}

export const isTransitioning = () => transitioning

/** Run `cb` once the page is visible: after the preloader and after any transition cover. */
export function whenPageVisible(cb: Cb): () => void {
  let cancelled = false
  const run = () => { if (!cancelled) cb() }
  const afterReady = () => {
    if (transitioning) enterListeners.add(run)
    else run()
  }
  const offReady = onAppReady(afterReady)
  return () => {
    cancelled = true
    offReady()
    enterListeners.delete(run)
  }
}
