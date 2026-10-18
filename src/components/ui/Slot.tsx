import type { ReactNode } from 'react'
import type { Img } from '~/content/site'

/** Renders the configured image if there is one, otherwise the procedural fallback. */
export function Slot({ image, children, className = 'slot' }: { image: Img; children: ReactNode; className?: string }) {
  if (!image) return <>{children}</>
  return <img className={className} src={image.src} alt={image.alt} loading="lazy" decoding="async" draggable={false} />
}
