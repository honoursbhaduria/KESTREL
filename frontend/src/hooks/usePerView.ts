import { useEffect, useState } from 'react'

/** How many carousel cells fit per view: `desktop` above 900px, `mobile` below. */
export function usePerView(desktop = 5, mobile = 2) {
  const [n, setN] = useState(desktop)
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 899px)')
    const update = () => setN(mq.matches ? mobile : desktop)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [desktop, mobile])
  return n
}
