import type { ReactNode } from 'react'

/** Small panel with a dark title strip, used for annotations over drawings. */
export function InfoBox({ title, children, foot, className = '' }: { title: string; children?: ReactNode; foot?: string; className?: string }) {
  return (
    <div className={`infobox ${className}`}>
      <div className="infobox__head mono" data-scramble key={title}>{title}</div>
      {children && <div className="infobox__body">{children}</div>}
      {foot && <div className="infobox__foot mono">[{foot}]</div>}
    </div>
  )
}
