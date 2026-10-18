/**
 * Design system tokens extracted directly from Kestrel drafting-paper specifications.
 * All values are exact, not eyeballed.
 */

export const tokens = {
  colors: {
    paper: '#f3f2ee',
    paper2: '#ecebe6',
    ink: '#282828',
    ink72: 'rgba(40, 40, 40, 0.72)',
    ink50: 'rgba(40, 40, 40, 0.5)',
    ink30: 'rgba(40, 40, 40, 0.3)',
    line: 'rgba(40, 40, 40, 0.22)',
    lineSoft: 'rgba(40, 40, 40, 0.12)',
    ghost: '#b4b4b0',
    accent: '#fa3600',
    ok: '#3c8a52',
    warn: '#c98a00',
    fail: '#fa3600',
    white: '#ffffff',
  },
  fonts: {
    sans: "'Inter Tight', 'Helvetica Neue', Arial, sans-serif",
    mono: "'Geist Mono', ui-monospace, Menlo, monospace",
  },
  fontSizes: {
    xs: '10.5px',
    mono: '11.5px',
    sm: '13px',
    body: '15px',
    h5: 'clamp(1.15rem, 1.6vw, 1.55rem)',
    h4: 'clamp(1.4rem, 2vw, 2rem)',
    h3: 'clamp(1.7rem, 2.6vw, 2.6rem)',
    h2: 'clamp(2.1rem, 3.6vw, 3.4rem)',
    h1: 'clamp(2.5rem, 4.2vw, 4.4rem)',
  },
  spacing: {
    inset: '8px',
    headerH: '56px',
    pad: 'clamp(16px, 1.8vw, 26px)',
  },
  shadows: {
    card: '0 4px 0 #282828',
    flag: '0 3px 0 #282828',
    subtle: '0 1px 3px rgba(40, 40, 40, 0.08)',
  },
  motion: {
    easeOut: 'cubic-bezier(0.22, 1, 0.36, 1)',
    easeInOut: 'cubic-bezier(0.76, 0, 0.24, 1)',
    ditherDuration: '0.58s',
    transitionDuration: '0.4s',
  },
} as const

export type Tokens = typeof tokens
