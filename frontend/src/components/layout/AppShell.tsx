import React from 'react'
import { Link, useNavigate } from '@tanstack/react-router'
import { api } from '~/api/client'
import { BracketLabel } from '~/components/shared/CoordLabel'

interface AppShellProps {
  children: React.ReactNode
  currentTab?: 'projects' | 'rulesets' | 'workspace' | 'settings'
}

export const AppShell: React.FC<AppShellProps> = ({ children, currentTab = 'projects' }) => {
  const navigate = useNavigate()
  const user = api.getUser()
  const org = api.getOrg()

  const handleLogout = async () => {
    await api.logout()
    navigate({ to: '/login' })
  }

  return (
    <div className="min-h-screen bg-[var(--paper)] text-[var(--ink)] flex flex-col pt-2 pb-4 px-2">
      {/* Top Drafting Bar */}
      <header
        className="h-14 border border-[var(--line)] bg-[var(--paper)] flex items-center justify-between px-3 sm:px-4 mb-2"
        style={{ boxShadow: '0 2px 0 var(--ink)' }}
      >
        <div className="flex items-center gap-3 sm:gap-4">
          <Link to="/" className="font-sans font-bold text-base sm:text-lg tracking-tight uppercase flex items-center gap-2">
            <span className="w-3.5 h-3.5 sm:w-4 sm:h-4 bg-[var(--accent)] inline-block" />
            KESTREL <span className="font-mono text-[10px] sm:text-[11px] font-normal text-[var(--ink-50)]">v0.1.0</span>
          </Link>
          <div className="h-4 w-[1px] bg-[var(--line)] hidden md:block" />
          {org && (
            <div className="hidden md:flex items-center gap-2 font-mono text-[11px]">
              <span className="text-[var(--ink-50)]">ORG:</span>
              <span className="font-semibold text-[var(--ink)]">{org.name}</span>
              <BracketLabel text="VERIFIED" />
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          {user ? (
            <div className="flex items-center gap-2 sm:gap-3 font-mono text-[11px]">
              <span className="hidden sm:inline text-[var(--ink-72)]">{user.full_name}</span>
              <button
                onClick={handleLogout}
                className="px-2 py-1 border border-[var(--line)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-colors uppercase text-[10px] sm:text-[10.5px]"
              >
                Logout
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="font-mono text-[10.5px] sm:text-[11px] px-2.5 sm:px-3 py-1 border border-[var(--line)] uppercase hover:border-[var(--ink)]"
              >
                Login
              </Link>
              <Link
                to="/register"
                className="font-mono text-[10.5px] sm:text-[11px] px-2.5 sm:px-3 py-1 bg-[var(--accent)] text-white uppercase"
              >
                Register
              </Link>
            </div>
          )}
        </div>
      </header>

      {/* Mobile Navigation Strip */}
      <nav className="flex md:hidden border border-[var(--line)] bg-[var(--paper)] mb-2 text-[11px] font-mono" style={{ boxShadow: '0 2px 0 var(--ink)' }}>
        <Link
          to="/projects"
          className={`flex-1 text-center py-2 px-2 uppercase whitespace-nowrap ${currentTab === 'projects' ? 'bg-[var(--ink)] text-white font-bold' : 'text-[var(--ink-72)] hover:bg-[var(--paper-2)]'}`}
        >
          [01] Projects
        </Link>
        <Link
          to="/pricing"
          className="flex-1 text-center py-2 px-2 uppercase whitespace-nowrap text-[var(--ink-50)] hover:bg-[var(--paper-2)] border-l border-[var(--line)]"
        >
          [02] Plans
        </Link>
        <Link
          to="/"
          className="flex-1 text-center py-2 px-2 uppercase whitespace-nowrap text-[var(--ink-50)] hover:bg-[var(--paper-2)] border-l border-[var(--line)]"
        >
          [03] Site
        </Link>
      </nav>

      {/* Main Workspace Frame */}
      <div className="flex-1 flex gap-2">
        {/* Left Sidebar Navigation */}
        <aside
          className="w-56 border border-[var(--line)] bg-[var(--paper)] p-3 flex flex-col justify-between hidden md:flex"
          style={{ boxShadow: '0 2px 0 var(--ink)' }}
        >
          <nav className="flex flex-col gap-1">
            <div className="font-mono text-[10px] text-[var(--ink-50)] uppercase tracking-widest px-2 py-1 mb-1">
              Architecture Modules
            </div>

            <Link
              to="/projects"
              className={`flex items-center justify-between px-3 py-2 font-mono text-[12px] uppercase transition-colors ${currentTab === 'projects' ? 'bg-[var(--ink)] text-white' : 'hover:bg-[var(--paper-2)] text-[var(--ink-72)]'}`}
            >
              <span>[01] Projects</span>
              <span className="text-[10px] opacity-60">CRUD</span>
            </Link>

            <div
              className={`flex items-center justify-between px-3 py-2 font-mono text-[12px] uppercase opacity-50 cursor-not-allowed text-[var(--ink-50)]`}
              title="Available in Phase 2"
            >
              <span>[02] Rulesets</span>
              <span className="text-[10px]">P2</span>
            </div>

            <div
              className={`flex items-center justify-between px-3 py-2 font-mono text-[12px] uppercase opacity-50 cursor-not-allowed text-[var(--ink-50)]`}
              title="Available in Phase 3"
            >
              <span>[03] Workspace</span>
              <span className="text-[10px]">P3</span>
            </div>

            <div
              className={`flex items-center justify-between px-3 py-2 font-mono text-[12px] uppercase opacity-50 cursor-not-allowed text-[var(--ink-50)]`}
              title="Available in Phase 6"
            >
              <span>[04] Settings</span>
              <span className="text-[10px]">P6</span>
            </div>
          </nav>

          {/* System status readout */}
          <div className="pt-3 border-t border-[var(--line)] font-mono text-[10.5px] text-[var(--ink-50)] flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span>SYSTEM:</span>
              <span className="text-[var(--ok)] font-semibold">ONLINE</span>
            </div>
            <div className="flex items-center justify-between">
              <span>DB / REDIS:</span>
              <span className="text-[var(--ok)]">HEALTHY</span>
            </div>
            <div className="flex items-center justify-between">
              <span>TENANCY:</span>
              <span className="text-[var(--ink)]">ISOLATED</span>
            </div>
          </div>
        </aside>

        {/* Content Area */}
        <main className="flex-1 flex flex-col border border-[var(--line)] bg-[var(--paper)] p-4 md:p-6 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
