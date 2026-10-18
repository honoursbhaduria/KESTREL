/**
 * Isometric line drawings built from a tiny projection helper.
 * Every icon here is generated, not traced.
 */
const C = Math.cos(Math.PI / 6)
const S = 0.5
/** Project a 3D point (x right, y depth, z up) to 2D isometric. */
export const p = (x: number, y: number, z: number) => [(x - y) * C, (x + y) * S - z] as const
export const pts = (list: [number, number, number][]) => list.map(([x, y, z]) => p(x, y, z).join(',')).join(' ')

export function Box({ x = 0, y = 0, z = 0, w, d, h, dash = false }: { x?: number; y?: number; z?: number; w: number; d: number; h: number; dash?: boolean }) {
  const top = pts([[x, y, z + h], [x + w, y, z + h], [x + w, y + d, z + h], [x, y + d, z + h]])
  const left = pts([[x, y + d, z], [x + w, y + d, z], [x + w, y + d, z + h], [x, y + d, z + h]])
  const right = pts([[x + w, y, z], [x + w, y + d, z], [x + w, y + d, z + h], [x + w, y, z + h]])
  const hidden = pts([[x, y, z], [x + w, y, z]]) + ' ' + pts([[x, y, z], [x, y + d, z]])
  return (
    <g>
      <polygon points={top} />
      <polygon points={left} />
      <polygon points={right} />
      {dash && <polyline className="dash" points={hidden} />}
    </g>
  )
}

const VB = '-110 -110 220 220'

import type { IsoKind } from '~/content/site'
export type { IsoKind }

export function Iso({ kind }: { kind: IsoKind }) {
  switch (kind) {
    case 'hand': // a single block being nudged by an arrow — manual edits
      return (
        <svg viewBox={VB} aria-hidden="true">
          <Box x={-30} y={-30} w={60} d={60} h={40} dash />
          <polyline points={pts([[50, -30, 20], [80, -30, 20]])} />
          <polyline points={pts([[70, -38, 20], [80, -30, 20], [70, -22, 20]])} />
          <polyline className="dash" points={pts([[-30, -30, 0], [-30, -30, -40]])} />
        </svg>
      )
    case 'gap': // two volumes separated by a dashed void — disconnected tools
      return (
        <svg viewBox={VB} aria-hidden="true">
          <Box x={-60} y={-20} w={40} d={40} h={70} />
          <Box x={20} y={-20} w={40} d={40} h={40} />
          <polyline className="dash" points={pts([[-20, 0, 35], [20, 0, 20]])} />
        </svg>
      )
    case 'blind': // a cube inside a dashed sphere outline — unseen issues
      return (
        <svg viewBox={VB} aria-hidden="true">
          <circle cx="0" cy="0" r="78" className="dash" />
          <Box x={-28} y={-28} z={-30} w={56} d={56} h={56} dash />
        </svg>
      )
    case 'pile': // stacked slabs — small tasks piling up
      return (
        <svg viewBox={VB} aria-hidden="true">
          {[0, 1, 2, 3].map((i) => <Box key={i} x={-50 + i * 4} y={-50 - i * 4} z={-40 + i * 22} w={90} d={90} h={12} />)}
        </svg>
      )
    case 'tower':
      return (
        <svg viewBox={VB} aria-hidden="true">
          <Box x={-40} y={-40} z={-60} w={80} d={80} h={30} />
          <Box x={-25} y={-25} z={-30} w={50} d={50} h={90} />
          <polyline className="acc-stroke" points={pts([[-25, -25, 60], [25, -25, 60]])} />
        </svg>
      )
    case 'room':
      return (
        <svg viewBox={VB} aria-hidden="true">
          <polygon className="ghost" points={pts([[-60, -60, -20], [60, -60, -20], [60, 60, -20], [-60, 60, -20]])} />
          <Box x={-60} y={-60} z={-20} w={6} d={120} h={60} />
          <Box x={-60} y={-60} z={-20} w={120} d={6} h={60} />
          <Box x={-10} y={10} z={-20} w={40} d={24} h={14} />
          <circle className="acc-stroke dash" cx={p(10, 22, -20)[0]} cy={p(10, 22, -20)[1]} r="34" />
        </svg>
      )
    case 'terrain':
      return (
        <svg viewBox={VB} aria-hidden="true">
          {[0, 1, 2, 3, 4].map((i) => (
            <polygon key={i} className={i === 2 ? 'acc-stroke' : ''} points={pts([[-70 + i * 10, -70 + i * 10, -40 + i * 14], [70 - i * 10, -70 + i * 10, -40 + i * 14], [70 - i * 10, 70 - i * 10, -40 + i * 14], [-70 + i * 10, 70 - i * 10, -40 + i * 14]])} />
          ))}
        </svg>
      )
    case 'grid':
      return (
        <svg viewBox={VB} aria-hidden="true">
          {[0, 1, 2].flatMap((i) => [0, 1, 2].map((j) => (
            <Box key={`${i}${j}`} x={-66 + i * 46} y={-66 + j * 46} z={-30} w={40} d={40} h={(i + j) % 3 === 0 ? 50 : 20} />
          )))}
        </svg>
      )
  }
}

/** Wide axonometric street scene for the intro panel. */
export function AxoScene() {
  const blocks: [number, number, number, number, number][] = [
    [-240, -40, 70, 70, 120], [-160, -40, 60, 70, 60], [-90, -40, 90, 70, 180],
    [10, -40, 70, 70, 90], [90, -40, 60, 70, 140], [160, -40, 80, 70, 70],
    [-240, 60, 120, 60, 40], [-110, 60, 80, 60, 100], [-20, 60, 130, 60, 50], [120, 60, 120, 60, 110],
  ]
  return (
    <svg viewBox="-330 -260 660 360" aria-hidden="true" style={{ fill: 'none', stroke: 'var(--ink-72)', strokeWidth: 0.9 }}>
      <g style={{ stroke: 'var(--line)' }}>
        {Array.from({ length: 13 }, (_, i) => -300 + i * 50).map((v) => (
          <g key={v}>
            <polyline points={pts([[v, -300, 0], [v, 300, 0]])} />
            <polyline points={pts([[-300, v, 0], [300, v, 0]])} />
          </g>
        ))}
      </g>
      {blocks.map(([x, y, w, d, h], i) => (
        <g key={i} className="axo-block" style={{ fill: 'var(--paper)' }}>
          <Box x={x} y={y} w={w} d={d} h={h} />
          {/* floor lines */}
          {Array.from({ length: Math.floor(h / 15) }, (_, k) => (
            <polyline key={k} style={{ stroke: 'var(--line)' }} points={pts([[x, y + d, (k + 1) * 15], [x + w, y + d, (k + 1) * 15], [x + w, y, (k + 1) * 15]])} />
          ))}
        </g>
      ))}
      <rect x={p(-90, -40, 180)[0] - 4} y={p(-90, -40, 180)[1] - 4} width="8" height="8" style={{ fill: 'var(--accent)', stroke: 'none' }} />
    </svg>
  )
}
