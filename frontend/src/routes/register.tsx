import { useState } from 'react'
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { api } from '~/api/client'
import { Button } from '~/components/shared/Button'
import { Card } from '~/components/shared/Card'
import { Input } from '~/components/shared/Input'
import { BracketLabel } from '~/components/shared/CoordLabel'
import { Toast } from '~/components/shared/Toast'

export const Route = createFileRoute('/register')({
  head: () => ({
    meta: [
      { title: 'Register — Haron Architectural Platform' },
      { name: 'description', content: 'Create a personal architecture studio on Haron' },
    ],
  }),
  component: RegisterPage,
})

function RegisterPage() {
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [orgName, setOrgName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await api.register({
        full_name: fullName,
        org_name: orgName || `${fullName}'s Studio`,
        email,
        password,
      })
      navigate({ to: '/projects' })
    } catch (err: any) {
      setError(err?.message || 'Registration failed. Please check inputs.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[var(--paper)] flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md flex flex-col gap-4">
        {/* Top Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[var(--line)]">
          <Link to="/" className="font-sans font-bold text-xl uppercase flex items-center gap-2">
            <span className="w-3.5 h-3.5 bg-[var(--accent)] inline-block" />
            HARON
          </Link>
          <BracketLabel text="STUDIO ONBOARDING" />
        </div>

        {error && (
          <Toast message={error} type="error" onClose={() => setError(null)} />
        )}

        <Card
          title="Studio Registration"
          subtitle="Creates Personal Org + Owner Membership"
          darkHeader
        >
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <Input
              label="Architect Full Name"
              required
              placeholder="Ar. Vikram Sethi"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />

            <Input
              label="Studio / Firm Name"
              placeholder="Sethi & Associates"
              helperText="Optional: Defaults to your name if empty"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
            />

            <Input
              label="Email Address"
              type="email"
              required
              placeholder="vikram@sethi-arch.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />

            <Input
              label="Password (min 8 chars)"
              type="password"
              required
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            <div className="pt-2">
              <Button
                type="submit"
                label={loading ? 'Creating Studio...' : 'Initialize Studio →'}
                variant="accent"
                className="w-full justify-center"
              />
            </div>
          </form>

          <div className="mt-5 pt-4 border-t border-[var(--line)] flex items-center justify-between font-mono text-[11px] text-[var(--ink-50)]">
            <span>Already have an account?</span>
            <Link to="/login" className="text-[var(--accent)] font-semibold hover:underline">
              [Sign In]
            </Link>
          </div>
        </Card>

        {/* Technical Footer */}
        <div className="flex items-center justify-between font-mono text-[10px] text-[var(--ink-50)] px-1">
          <span>STORAGE: POSTGRES + POSTGIS</span>
          <span>MULTI-TENANT: STRICT</span>
        </div>
      </div>
    </div>
  )
}
