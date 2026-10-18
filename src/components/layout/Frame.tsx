/** Fixed drawing-sheet frame: 1px border inset from the viewport with tick marks down each side. */
export function Frame() {
  return (
    <div className="frame" aria-hidden="true">
      <span className="frame__side frame__side--l" />
      <span className="frame__side frame__side--r" />
    </div>
  )
}
