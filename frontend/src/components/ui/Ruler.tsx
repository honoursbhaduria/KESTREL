/** Horizontal ruler band with crosshair marks at each end. */
export function Ruler({ className = '' }: { className?: string }) {
  return (
    <div className={`ruler ${className}`} aria-hidden="true">
      <span className="plus" />
      <span className="ruler__ticks" />
      <span className="plus" />
    </div>
  )
}
