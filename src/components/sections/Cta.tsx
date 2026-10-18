import { useRef, useState, type FormEvent } from 'react'
import { Button } from '~/components/ui/Button'
import { SplitText } from '~/components/ui/SplitText'
import { useSectionReveal } from '~/hooks/useSplitReveal'
import { cta } from '~/content/site'

type Status = 'idle' | 'error' | 'sent'

export function Cta() {
  const ref = useRef<HTMLElement>(null)
  const [status, setStatus] = useState<Status>('idle')
  useSectionReveal(ref)

  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const input = e.currentTarget.elements.namedItem('email') as HTMLInputElement
    if (!input.checkValidity()) { setStatus('error'); input.focus(); return }
    // No backend in this build: connect to a server function or form endpoint
    setStatus('sent')
    e.currentTarget.reset()
  }

  return (
    <section className="cta sec" id="contact" ref={ref}>
      <div className="cta__grid">
        <span className="cta__corner mono">[0, 0]</span>
        <span className="cta__corner mono" />
        <span className="cta__corner mono" />
        <span className="cta__corner mono">[1200, 0]</span>
        <div className="cta__main">
          <SplitText className="h2" text={cta.title} />
          <p className="body fade-up">{cta.body}</p>
          <form className="cta__form fade-up" noValidate onSubmit={submit}>
            <label className="sr-only" htmlFor="email">Work email</label>
            <input id="email" type="email" name="email" placeholder={cta.placeholder} required autoComplete="email"
              aria-invalid={status === 'error'} aria-describedby="cta-msg" onInput={() => status !== 'idle' && setStatus('idle')} />
            <Button type="submit" label={cta.button} />
          </form>
          <p className="cta__msg mono" id="cta-msg" role="status">
            {status === 'error' && cta.error}
            {status === 'sent' && cta.success}
          </p>
        </div>
        <span className="cta__corner mono">[0, 800]</span>
        <span className="cta__corner mono" />
        <span className="cta__corner mono" />
        <span className="cta__corner mono">[1200, 800]</span>
      </div>
    </section>
  )
}
