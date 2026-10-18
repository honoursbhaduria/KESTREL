import { useEffect, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { Button } from '~/components/ui/Button'
import { onAppReady } from '~/lib/ready'
import { cookie } from '~/content/site'

const KEY = 'kestrel-cookie-choice'

export function CookieBanner() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let stored: string | null = null
    try { stored = localStorage.getItem(KEY) } catch { /* storage blocked */ }
    if (stored) return
    let t = 0
    const off = onAppReady(() => { t = window.setTimeout(() => setOpen(true), 1200) })
    return () => { off(); clearTimeout(t) }
  }, [])

  const choose = (value: 'accept' | 'reject') => {
    try { localStorage.setItem(KEY, value) } catch { /* storage blocked */ }
    setOpen(false)
  }

  if (!open) return null
  return (
    <div className="cookie" role="dialog" aria-label="Cookie notice">
      <p>{cookie.text} <Link to="/privacy" hash="cookies" className="cookie__more mono">{cookie.more}</Link></p>
      <div className="cookie__actions">
        <Button label={cookie.accept} size="sm" icon={null} onClick={() => choose('accept')} />
        <Button label={cookie.reject} size="sm" variant="ghost" icon={null} onClick={() => choose('reject')} />
      </div>
    </div>
  )
}
