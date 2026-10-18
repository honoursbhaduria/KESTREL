/**
 * Hero drawing: a procedurally rendered building elevation in ink on paper.
 * Concrete volumes are stippled, glazing is hatched, trees are grown with a
 * seeded branching routine. Dragging sweeps a scan lens; issues inside the
 * lens are revealed and reported through `onReveal`.
 *
 * Drawing space is 1000 × 520 units, scaled to fit the canvas.
 */

import { hero } from '~/content/site'

export type Issue = { id: string; x: number; y: number; code: string; text: string }

export const ISSUES: Issue[] = hero.issues

export type Rect = [number, number, number, number] // x, y, w, h
export const W = 1000
export const H = 520
export const GROUND = 470
/** Fraction of the canvas the drawing fills; shared with the preloader so they line up. */
export const FIT = 0.92

// Building volumes (concrete) — stippled
export const SOLIDS: Rect[] = [
  [230, 250, 170, 220],  // west wing
  [400, 140, 330, 330],  // central block
  [560, 100, 250, 140],  // cantilevered upper box
  [730, 250, 130, 220],  // east wing
  [250, 420, 120, 50],   // plinth under stair
]
// Glazing panes — hatched
export const GLASS: Rect[] = [
  [420, 170, 120, 110], [420, 300, 120, 110],
  [580, 120, 210, 90],
  [580, 300, 130, 110],
  [745, 280, 100, 60],
  [250, 280, 60, 90],
]
// Vertical fins on the upper box
export const FINS = Array.from({ length: 9 }, (_, i) => 590 + i * 24)

/** Small deterministic PRNG so the drawing is identical on every load. */
function rng(seed: number) {
  return () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296
    return seed / 4294967296
  }
}

type Seg = [number, number, number, number, number] // x1 y1 x2 y2 width

function growTree(x: number, y: number, size: number, seed: number): Seg[] {
  const r = rng(seed)
  const out: Seg[] = []
  const branch = (bx: number, by: number, len: number, ang: number, depth: number) => {
    const ex = bx + Math.cos(ang) * len
    const ey = by + Math.sin(ang) * len
    out.push([bx, by, ex, ey, Math.max(0.4, depth * 0.55)])
    if (depth <= 0) return
    const n = depth > 3 ? 2 : 2 + (r() > 0.5 ? 1 : 0)
    for (let i = 0; i < n; i++) {
      branch(ex, ey, len * (0.66 + r() * 0.14), ang + (r() - 0.5) * 1.1, depth - 1)
    }
  }
  branch(x, y, size, -Math.PI / 2 + (r() - 0.5) * 0.1, 6)
  return out
}

export class PlanCanvas {
  private ctx: CanvasRenderingContext2D
  private w = 0
  private h = 0
  private dpr = 1
  private lens = { x: 500, y: 300, r: 0, tr: 0 }
  private pointer = { x: 500, y: 300 }
  private dragging = false
  private revealed = new Set<string>()
  private raf = 0
  private t = 0
  private intro = 0
  private ro: ResizeObserver
  private io: IntersectionObserver
  private visible = true
  private keyTimer = 0
  private stipple: [number, number, number][] = []
  private trees: Seg[] = []

  constructor(
    private canvas: HTMLCanvasElement,
    private opts: { onMove?: (x: number, y: number) => void; onReveal?: (issue: Issue) => void; reduced?: boolean; overlayOnly?: boolean } = {},
  ) {
    this.ctx = canvas.getContext('2d')!
    this.buildStatic()
    this.ro = new ResizeObserver(() => this.resize())
    this.ro.observe(canvas)
    this.io = new IntersectionObserver(([e]) => { this.visible = e.isIntersecting })
    this.io.observe(canvas)
    this.resize()
    this.bind()
    if (opts.reduced) this.intro = 1
    this.loop = this.loop.bind(this)
    this.raf = requestAnimationFrame(this.loop)
  }

  /** Precompute stipple dots (denser toward the lower-right of each volume) and trees. */
  private buildStatic() {
    const r = rng(7)
    for (const [x, y, w, h] of SOLIDS) {
      const n = Math.round((w * h) / 22)
      for (let i = 0; i < n; i++) {
        const u = r(), v = r()
        // bias density: shadow side gets more dots
        if (r() > 0.35 + u * 0.5) continue
        this.stipple.push([x + u * w, y + v * h, r() * 0.9 + 0.3])
      }
    }
    this.trees = [
      ...growTree(150, GROUND, 62, 3),
      ...growTree(195, GROUND, 48, 11),
      ...growTree(915, GROUND, 62, 5),
      ...growTree(960, GROUND, 44, 21),
    ]
  }

  private get view() {
    const s = Math.min(this.w / W, this.h / H) * FIT
    return { s, ox: (this.w - W * s) / 2, oy: (this.h - H * s) / 2 }
  }

  private resize() {
    const r = this.canvas.getBoundingClientRect()
    this.dpr = Math.min(window.devicePixelRatio || 1, 2)
    this.w = r.width
    this.h = r.height
    this.canvas.width = Math.round(r.width * this.dpr)
    this.canvas.height = Math.round(r.height * this.dpr)
  }

  private toDrawing(e: PointerEvent) {
    const r = this.canvas.getBoundingClientRect()
    const { s, ox, oy } = this.view
    return { x: (e.clientX - r.left - ox) / s, y: (e.clientY - r.top - oy) / s }
  }

  private onDown = (e: PointerEvent) => {
    this.dragging = true
    this.canvas.setPointerCapture(e.pointerId)
    Object.assign(this.pointer, this.toDrawing(e))
    this.lens.tr = 70
  }
  private onMove = (e: PointerEvent) => {
    const p = this.toDrawing(e)
    Object.assign(this.pointer, p)
    this.opts.onMove?.(Math.max(0, Math.round(p.x * 24)), Math.max(0, Math.round((GROUND - p.y) * 24)))
  }
  private onUp = () => { this.dragging = false; this.lens.tr = 0 }
  private onKey = (e: KeyboardEvent) => {
    const d: Record<string, [number, number]> = { ArrowLeft: [-30, 0], ArrowRight: [30, 0], ArrowUp: [0, -30], ArrowDown: [0, 30] }
    if (!d[e.key]) return
    e.preventDefault()
    this.pointer.x = Math.min(W, Math.max(0, this.pointer.x + d[e.key][0]))
    this.pointer.y = Math.min(H, Math.max(0, this.pointer.y + d[e.key][1]))
    this.lens.tr = 70
    this.dragging = true
    clearTimeout(this.keyTimer)
    this.keyTimer = window.setTimeout(this.onUp, 900)
  }

  private bind() {
    this.canvas.addEventListener('pointerdown', this.onDown)
    this.canvas.addEventListener('pointermove', this.onMove)
    this.canvas.addEventListener('pointerup', this.onUp)
    this.canvas.addEventListener('pointercancel', this.onUp)
    this.canvas.addEventListener('keydown', this.onKey)
  }

  playIntro(duration = 2.4) {
    const start = performance.now()
    const step = (now: number) => {
      this.intro = Math.min(1, (now - start) / (duration * 1000))
      if (this.intro < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }

  private loop(now: number) {
    this.raf = requestAnimationFrame(this.loop)
    if (!this.visible) return
    this.t = now / 1000
    const k = this.dragging ? 0.3 : 0.12
    this.lens.x += (this.pointer.x - this.lens.x) * k
    this.lens.y += (this.pointer.y - this.lens.y) * k
    this.lens.r += (this.lens.tr - this.lens.r) * 0.15
    this.detect()
    this.draw()
  }

  private detect() {
    if (this.lens.r < 10) return
    for (const issue of ISSUES) {
      if (this.revealed.has(issue.id)) continue
      if (Math.hypot(issue.x - this.lens.x, issue.y - this.lens.y) < this.lens.r) {
        this.revealed.add(issue.id)
        this.opts.onReveal?.(issue)
      }
    }
  }

  private draw() {
    const { ctx, dpr } = this
    const { s, ox, oy } = this.view
    const e = 1 - Math.pow(1 - this.intro, 3)
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, this.w, this.h)
    ctx.setTransform(dpr * s, 0, 0, dpr * s, dpr * ox, dpr * oy)
    const ink = '40,40,40'
    const lw = 1 / s // one CSS pixel

    // Construction lines: dashed guides through every volume edge, plus two orange datums
    const ca = Math.min(1, e * 1.6)
    ctx.setLineDash([6 * lw, 5 * lw])
    ctx.lineWidth = 1 * lw
    ctx.strokeStyle = `rgba(${ink},${0.16 * ca})`
    ctx.beginPath()
    const xs = new Set<number>(), ys = new Set<number>()
    for (const [x, y, w] of SOLIDS) { xs.add(x); xs.add(x + w); ys.add(y) }
    xs.forEach((x) => { ctx.moveTo(x, -60); ctx.lineTo(x, GROUND) })
    ys.forEach((y) => { ctx.moveTo(-60, y); ctx.lineTo(1060, y) })
    ctx.stroke()
    ctx.setLineDash([])
    ctx.strokeStyle = `rgba(250,54,0,${0.7 * ca})`
    ctx.beginPath()
    ctx.moveTo(400, -40); ctx.lineTo(400 + 470 * ca, -40)   // roof datum
    ctx.moveTo(-40, 250); ctx.lineTo(-40, 250 + 220 * ca)   // wing datum
    ctx.stroke()

    if (!this.opts.overlayOnly) this.drawBuilding(e, lw, ink)
    this.drawOverlay(e, lw)
  }

  /** The procedural elevation: ground, volumes, stipple, glazing, fins, stair, trees. */
  private drawBuilding(e: number, lw: number, ink: string) {
    const { ctx } = this
    // Ground line draws first
    ctx.strokeStyle = `rgba(${ink},0.9)`
    ctx.lineWidth = 1.6 * lw
    ctx.beginPath(); ctx.moveTo(40, GROUND); ctx.lineTo(40 + 950 * Math.min(1, e * 2.5), GROUND); ctx.stroke()

    const a = Math.max(0, Math.min(1, (e - 0.15) / 0.6)) // volumes fade/rise
    // Volumes: paper fill then outline, rising from the ground
    for (const [x, y, w, h] of SOLIDS) {
      const hh = h * a
      ctx.fillStyle = '#f3f2ee'
      ctx.fillRect(x, y + (h - hh), w, hh)
      ctx.strokeStyle = `rgba(${ink},0.9)`
      ctx.lineWidth = 1.2 * lw
      ctx.strokeRect(x, y + (h - hh), w, hh)
    }

    // Stipple
    const sa = Math.max(0, (e - 0.45) / 0.55)
    if (sa > 0) {
      ctx.fillStyle = `rgba(${ink},${0.55 * sa})`
      for (const [x, y, r] of this.stipple) ctx.fillRect(x, y, r * lw * 1.4, r * lw * 1.4)
    }

    // Glazing: light fill, mullions, diagonal hatching
    if (a > 0.6) {
      const ga = (a - 0.6) / 0.4
      for (const [x, y, w, h] of GLASS) {
        ctx.fillStyle = '#e6e5df'
        ctx.fillRect(x, y, w, h)
        ctx.strokeStyle = `rgba(${ink},${0.8 * ga})`
        ctx.lineWidth = 1 * lw
        ctx.strokeRect(x, y, w, h)
        ctx.save()
        ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip()
        ctx.strokeStyle = `rgba(${ink},${0.18 * ga})`
        ctx.beginPath()
        for (let d = -h; d < w; d += 7) { ctx.moveTo(x + d, y + h); ctx.lineTo(x + d + h, y) }
        ctx.stroke()
        ctx.strokeStyle = `rgba(${ink},${0.6 * ga})`
        ctx.beginPath()
        for (let mx = x + w / 3; mx < x + w - 1; mx += w / 3) { ctx.moveTo(mx, y); ctx.lineTo(mx, y + h) }
        ctx.moveTo(x, y + h * 0.5); ctx.lineTo(x + w, y + h * 0.5)
        ctx.stroke()
        ctx.restore()
      }
      // Fins on upper box
      ctx.strokeStyle = `rgba(${ink},${0.9 * ga})`
      ctx.lineWidth = 3 * lw
      ctx.beginPath()
      for (const fx of FINS) { ctx.moveTo(fx, 104); ctx.lineTo(fx, 236) }
      ctx.stroke()
      // Stair treads
      ctx.lineWidth = 1 * lw
      ctx.beginPath()
      for (let i = 0; i < 8; i++) { const sy = 420 + i * 6.25; ctx.moveTo(250, sy); ctx.lineTo(370 - i * 6, sy) }
      ctx.stroke()
      // Roof terrace guard (the GRD-02 issue: short)
      ctx.beginPath(); ctx.moveTo(560, 100); ctx.lineTo(560, 88); ctx.lineTo(810, 88); ctx.lineTo(810, 100); ctx.stroke()
    }

    // Trees grow in last
    const ta = Math.max(0, (e - 0.35) / 0.65)
    if (ta > 0) {
      ctx.strokeStyle = `rgba(${ink},0.75)`
      const count = Math.floor(this.trees.length * ta)
      for (let i = 0; i < count; i++) {
        const [x1, y1, x2, y2, w] = this.trees[i]
        ctx.lineWidth = w * lw
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
      }
    }

  }

  /** Markers and scan lens: drawn over either the procedural building or a supplied image. */
  private drawOverlay(e: number, lw: number) {
    const { ctx } = this
    // Issue squares: always visible once drawn, pulse gently
    if (e > 0.9) {
      for (const issue of ISSUES) {
        const found = this.revealed.has(issue.id)
        const pulse = (Math.sin(this.t * 3 + issue.x) + 1) / 2
        const size = (found ? 12 : 9) * lw
        ctx.fillStyle = '#fa3600'
        ctx.fillRect(issue.x - size / 2, issue.y - size / 2, size, size)
        if (!found) {
          ctx.strokeStyle = `rgba(250,54,0,${0.5 - pulse * 0.4})`
          ctx.lineWidth = 1 * lw
          const ring = size + pulse * 14 * lw
          ctx.strokeRect(issue.x - ring / 2, issue.y - ring / 2, ring, ring)
        } else {
          ctx.font = `${10 * lw}px "Geist Mono", monospace`
          ctx.fillStyle = 'rgba(40,40,40,0.9)'
          ctx.fillText(issue.code, issue.x + 10 * lw, issue.y - 8 * lw)
        }
      }
    }

    // Scan lens
    if (this.lens.r > 1) {
      const { x, y, r } = this.lens
      ctx.save()
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(250,54,0,0.06)'; ctx.fill()
      ctx.clip()
      ctx.strokeStyle = 'rgba(250,54,0,0.22)'
      ctx.lineWidth = 1 * lw
      ctx.beginPath()
      const off = (this.t * 20) % 6
      for (let yy = y - r + off; yy < y + r; yy += 6) { ctx.moveTo(x - r, yy); ctx.lineTo(x + r, yy) }
      ctx.stroke()
      ctx.restore()
      ctx.strokeStyle = '#fa3600'
      ctx.setLineDash([4 * lw, 4 * lw]); ctx.lineDashOffset = -this.t * 20 * lw
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke()
      ctx.setLineDash([])
      ctx.beginPath()
      ctx.moveTo(x - 8 * lw, y); ctx.lineTo(x + 8 * lw, y); ctx.moveTo(x, y - 8 * lw); ctx.lineTo(x, y + 8 * lw)
      ctx.stroke()
    }
  }

  destroy() {
    cancelAnimationFrame(this.raf)
    clearTimeout(this.keyTimer)
    this.ro.disconnect()
    this.io.disconnect()
    this.canvas.removeEventListener('pointerdown', this.onDown)
    this.canvas.removeEventListener('pointermove', this.onMove)
    this.canvas.removeEventListener('pointerup', this.onUp)
    this.canvas.removeEventListener('pointercancel', this.onUp)
    this.canvas.removeEventListener('keydown', this.onKey)
  }
}
