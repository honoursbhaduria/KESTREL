import { useEffect, useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { api, type Project } from '~/api/client'
import { AppShell } from '~/components/layout/AppShell'
import { Button } from '~/components/shared/Button'
import { Card } from '~/components/shared/Card'
import { Input } from '~/components/shared/Input'
import { Modal } from '~/components/shared/Modal'
import { StatusPill } from '~/components/shared/StatusPill'
import { BracketLabel, CoordLabel } from '~/components/shared/CoordLabel'
import { Toast } from '~/components/shared/Toast'

export const Route = createFileRoute('/projects/')({
  head: () => ({
    meta: [
      { title: 'Projects — Kestrel Architectural Platform' },
      { name: 'description', content: 'Studio project workspace and active commissions' },
    ],
  }),
  component: ProjectsPage,
})

function ProjectsPage() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toastMsg, setToastMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  // New Project Modal State
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDesc, setNewProjectDesc] = useState('')
  const [creating, setCreating] = useState(false)

  const fetchProjects = async () => {
    try {
      setLoading(true)
      const data = await api.listProjects()
      setProjects(data.items)
    } catch (err: any) {
      if (!api.isAuthenticated()) {
        navigate({ to: '/login' })
        return
      }
      setError(err?.message || 'Failed to fetch projects')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!api.isAuthenticated()) {
      navigate({ to: '/login' })
      return
    }
    fetchProjects()
  }, [])

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newProjectName.trim()) return

    setCreating(true)
    try {
      const project = await api.createProject({
        name: newProjectName.trim(),
        description: newProjectDesc.trim() || undefined,
      })
      setProjects([project, ...projects])
      setIsModalOpen(false)
      setNewProjectName('')
      setNewProjectDesc('')
      setToastMsg({ text: `Project "${project.name}" initialized`, type: 'success' })
    } catch (err: any) {
      setToastMsg({ text: err?.message || 'Failed to create project', type: 'error' })
    } finally {
      setCreating(false)
    }
  }

  const handleDeleteProject = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete "${name}"?`)) return

    try {
      await api.deleteProject(id)
      setProjects(projects.filter((p) => p.id !== id))
      setToastMsg({ text: `Project "${name}" deleted`, type: 'success' })
    } catch (err: any) {
      setToastMsg({ text: err?.message || 'Failed to delete project', type: 'error' })
    }
  }

  return (
    <AppShell currentTab="projects">
      <div className="flex flex-col gap-6 max-w-6xl w-full mx-auto">
        {/* Screen Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--line)]">
          <div>
            <div className="flex items-center gap-2">
              <BracketLabel text="01" accent />
              <h1 className="font-sans font-bold text-2xl uppercase tracking-tight text-[var(--ink)]">
                Active Commissions
              </h1>
              <span className="font-mono text-xs px-2 py-0.5 bg-[var(--paper-2)] border border-[var(--line)] text-[var(--ink-72)]">
                {projects.length} Total
              </span>
            </div>
            <p className="font-mono text-[12px] text-[var(--ink-50)] mt-1">
              Deterministic geometry · PostGIS spatial envelopes · Multi-tenant isolation
            </p>
          </div>

          <Button
            label="+ New Project"
            variant="accent"
            size="md"
            onClick={() => setIsModalOpen(true)}
          />
        </div>

        {toastMsg && (
          <Toast
            message={toastMsg.text}
            type={toastMsg.type}
            onClose={() => setToastMsg(null)}
          />
        )}

        {error && (
          <Toast message={error} type="error" onClose={() => setError(null)} />
        )}

        {/* Content Section: Loading, Empty, or Projects Grid */}
        {loading ? (
          <div className="flex flex-col items-center justify-center p-12 font-mono text-[13px] text-[var(--ink-50)] gap-2">
            <span className="animate-spin inline-block w-5 h-5 border-2 border-[var(--accent)] border-t-transparent rounded-full" />
            <span>Scanning project repository...</span>
          </div>
        ) : projects.length === 0 ? (
          /* Empty Project State */
          <div className="border border-dashed border-[var(--line)] p-12 text-center flex flex-col items-center gap-4 bg-[var(--paper-2)]">
            <div className="w-12 h-12 border border-[var(--line)] flex items-center justify-center font-mono text-lg text-[var(--ink-50)]">
              [+]
            </div>
            <div>
              <h3 className="font-mono font-semibold text-sm uppercase text-[var(--ink)]">
                No Active Projects In Organization
              </h3>
              <p className="font-mono text-[12px] text-[var(--ink-50)] max-w-md mt-1">
                Start by creating a new project. You will define the plot boundary, select the
                governing jurisdiction bylaws, and generate code-compliant floor plans.
              </p>
            </div>
            <Button
              label="Initialize First Project"
              variant="accent"
              size="sm"
              onClick={() => setIsModalOpen(true)}
            />
          </div>
        ) : (
          /* Projects Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((proj, idx) => (
              <Card
                key={proj.id}
                title={proj.name}
                subtitle={`PROJ-${idx + 1 < 10 ? '0' : ''}${idx + 1}`}
                badge={<StatusPill status="pass" label={proj.status} />}
                onClick={() =>
                  navigate({
                    to: '/projects/$projectId',
                    params: { projectId: proj.id },
                  })
                }
              >
                <div className="flex flex-col gap-3">
                  <p className="font-mono text-[12px] text-[var(--ink-72)] line-clamp-2 min-h-[36px]">
                    {proj.description || 'Architectural program and spatial layout'}
                  </p>

                  <div className="pt-2 border-t border-[var(--line-soft)] flex items-center justify-between text-[11px]">
                    <CoordLabel axis="X" value={8400 + idx * 450} unit="MM" />
                    <CoordLabel axis="Y" value={6200 + idx * 300} unit="MM" />
                  </div>

                  <div className="pt-2 flex items-center justify-between border-t border-[var(--line)]">
                    <span className="font-mono text-[10px] text-[var(--ink-50)]">
                      {new Date(proj.created_at).toLocaleDateString()}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteProject(proj.id, proj.name)
                        }}
                        className="font-mono text-[11px] text-[var(--ink-50)] hover:text-[var(--accent)]"
                        title="Delete Project"
                      >
                        [Delete]
                      </button>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* New Project Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Initialize Architectural Project"
      >
        <form onSubmit={handleCreateProject} className="flex flex-col gap-4">
          <Input
            label="Project Title"
            required
            placeholder="e.g. Vasant Vihar Villa, Sector 42"
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
          />

          <div className="flex flex-col gap-1 text-left">
            <label className="font-mono text-[11px] uppercase tracking-wider text-[var(--ink-72)]">
              Brief Summary / Context
            </label>
            <textarea
              className="p-3 font-mono text-[12px] bg-[var(--paper)] text-[var(--ink)] border border-[var(--line)] outline-none min-h-[80px]"
              placeholder="e.g. 3-storey contemporary residence on a 300 sqm plot, vastu compliant."
              value={newProjectDesc}
              onChange={(e) => setNewProjectDesc(e.target.value)}
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--line)]">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-3 py-1.5 font-mono text-[11px] uppercase text-[var(--ink-72)] hover:text-[var(--ink)]"
            >
              Cancel
            </button>
            <Button
              type="submit"
              label={creating ? 'Saving...' : 'Create Project →'}
              variant="accent"
              size="sm"
            />
          </div>
        </form>
      </Modal>
    </AppShell>
  )
}
