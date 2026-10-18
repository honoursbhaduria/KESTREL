#!/usr/bin/env node
/**
 * Generates public/mask-dither.svg: a horizontal sprite of 20 frames used as a CSS mask
 * for the stepped button fill. Each frame is a 16×4 grid of square cells; a cell is
 * filled when (left-to-right wipe + Bayer dither) falls under the frame's threshold,
 * so the fill sweeps across in a pixelated, ordered-dither pattern.
 */
import { writeFileSync } from 'node:fs'

const FRAMES = 20
const COLS = 16
const ROWS = 4
const CELL = 4
const BAYER = [
  [0, 8, 2, 10],
  [12, 4, 14, 6],
  [3, 11, 1, 9],
  [15, 7, 13, 5],
]

const fw = COLS * CELL
const fh = ROWS * CELL
const rects = []
for (let f = 0; f < FRAMES; f++) {
  const threshold = f / (FRAMES - 1) // 0 → nothing, 1 → everything
  for (let x = 0; x < COLS; x++) {
    for (let y = 0; y < ROWS; y++) {
      const v = 0.65 * (x / (COLS - 1)) + 0.35 * (BAYER[y % 4][x % 4] / 15)
      if (f > 0 && v <= threshold) rects.push(`M${f * fw + x * CELL} ${y * CELL}h${CELL}v${CELL}h-${CELL}z`)
    }
  }
}
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${fw * FRAMES} ${fh}" preserveAspectRatio="none" shape-rendering="crispEdges"><path d="${rects.join('')}"/></svg>\n`
writeFileSync(new URL('../public/mask-dither.svg', import.meta.url), svg)
console.log(`public/mask-dither.svg — ${FRAMES} frames, ${rects.length} cells, ${svg.length} bytes`)
