import { useState } from 'react'
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { api } from '~/api/client'
import { Button } from '~/components/shared/Button'
import { Card } from '~/components/shared/Card'
import { Input } from '~/components/shared/Input'
import { BracketLabel } from '~/components/shared/CoordLabel'
import { Toast } from '~/components/shared/Toast'

export const Route = createFileRoute('/login')({
  head: () => ({
    meta: [
      { title: 'Login — Haron Architectural Platform' },
      { name: 'description', content: 'Sign in to Haron AI Home Design Platform for Architects' },
    ],
  }),
  component: LoginPage,
})

function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await api.login({ email, password })
      navigate({ to: '/projects' })
    } catch (err: any) {
      setError(err?.message || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[var(--paper)] flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md flex flex-col gap-4">
        {/* Top Logo and Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[var(--line)]">
          <Link to="/" className="font-sans font-bold text-xl uppercase flex items-center gap-2">
            <span className="w-3.5 h-3.5 bg-[var(--accent)] inline-block" />
            HARON
          </Link>
          <BracketLabel text="AUTH · 01" />
        </div>

        {error && (
          <Toast message={error} type="error" onClose={() => setError(null)} />
        )}

        <Card
          title="Architect Access"
          subtitle="JWT Authentication · Scoped Organization"
          darkHeader
        >
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label="Email Address"
              type="email"
              required
              placeholder="architect@studio.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />

            <Input
              label="Password"
              type="password"
              required
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            <div className="pt-2">
              <Button
                type="submit"
                label={loading ? 'Authenticating...' : 'Sign In →'}
                variant="accent"
                className="w-full justify-center"
              />
            </div>
          </form>

          <div className="mt-6 pt-4 border-t border-[var(--line)] flex items-center justify-between font-mono text-[11px] text-[var(--ink-50)]">
            <span>No account yet?</span>
            <Link to="/register" className="text-[var(--accent)] font-semibold hover:underline">
              [Register Studio]
            </Link>
          </div>
        </Card>

        {/* Footer Technical Metadata */}
        <div className="flex items-center justify-between font-mono text-[10px] text-[var(--ink-50)] px-1">
          <span>PORT: 8001</span>
          <span>SYSTEM: READY</span>
          <span>SECURITY: ARGON2</span>
        </div>
      </div>
    </div>
  )
}
