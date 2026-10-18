import { useEffect, useState } from 'react'
import { createFileRoute, Link, useNavigate, useParams } from '@tanstack/react-router'
import {
  api,
  type Envelope,
  type Plot,
  type Project,
  type RulesetSummary,
  type RuleSearchResult,
} from '~/api/client'
import { PlanWorkspace } from '~/components/plan/PlanWorkspace'
import { PlanGenerator } from '~/components/plan/PlanGenerator'
import { AppShell } from '~/components/layout/AppShell'
import { Button } from '~/components/shared/Button'
import { Card } from '~/components/shared/Card'
import { Input } from '~/components/shared/Input'
import { StatusPill } from '~/components/shared/StatusPill'
import { BracketLabel, CoordLabel } from '~/components/shared/CoordLabel'
import { DataRow } from '~/components/shared/DataRow'
import { Toast } from '~/components/shared/Toast'

export const Route = createFileRoute('/projects/$projectId')({
  head: () => ({
    meta: [
      { title: 'Plan Workspace & Spatial Envelope — Kestrel Architectural Platform' },
      { name: 'description', content: '2D interactive plan drafting workspace, buildable envelope and statutory review' },
    ],
  }),
  component: ProjectPlotEnvelopePage,
})

function ProjectPlotEnvelopePage() {
  const { projectId } = useParams({ from: '/projects/$projectId' })
  const navigate = useNavigate()

  const [project, setProject] = useState<Project | null>(null)
  const [plot, setPlot] = useState<Plot | null>(null)
  const [envelope, setEnvelope] = useState<Envelope | null>(null)
  const [rulesets, setRulesets] = useState<RulesetSummary[]>([])
  const [selectedRulesetId, setSelectedRulesetId] = useState<string>('india-nbc-2016')
  const [activeTab, setActiveTab] = useState<'generator' | 'workspace' | 'envelope' | 'rag'>('generator')
  const [workspacePlanId, setWorkspacePlanId] = useState<string | undefined>(undefined)

  // Plot Form Inputs (Width x Depth)
  const [widthMeters, setWidthMeters] = useState('15')
  const [depthMeters, setDepthMeters] = useState('20')
  const [northAngle, setNorthAngle] = useState(0)
  const [roadWidthMeters, setRoadWidthMeters] = useState('12')
  const [roadEdgeIndex, setRoadEdgeIndex] = useState(0)

  // Hover Coordinates on SVG Canvas
  const [hoverCoord, setHoverCoord] = useState<{ x: number; y: number } | null>(null)

  // RAG Search State
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<RuleSearchResult[]>([])
  const [searching, setSearching] = useState(false)

  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [toastMsg, setToastMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  const loadData = async () => {
    try {
      setLoading(true)
      const [projData, rulesetsData] = await Promise.all([
        api.getProject(projectId),
        api.listRulesets(),
      ])
      setProject(projData)
      setRulesets(rulesetsData)
      if (projData.ruleset_id) {
        setSelectedRulesetId(projData.ruleset_id)
      }

      // Try loading plot
      try {
        const plotData = await api.getPlot(projectId)
        setPlot(plotData)
        setNorthAngle(plotData.north_angle_deg || 0)

        // Try loading envelope
        const envData = await api.getEnvelope(projectId)
        setEnvelope(envData)
      } catch {
        // Plot not yet defined
      }
    } catch (err: any) {
      if (!api.isAuthenticated()) {
        navigate({ to: '/login' })
        return
      }
      setToastMsg({ text: err?.message || 'Failed to load project details', type: 'error' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [projectId])

  const handleSavePlot = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    setUpdating(true)
    try {
      const wMm = parseFloat(widthMeters) * 1000
      const dMm = parseFloat(depthMeters) * 1000
      const roadMm = parseFloat(roadWidthMeters) * 1000

      if (isNaN(wMm) || isNaN(dMm) || wMm <= 0 || dMm <= 0) {
        throw new Error('Please enter valid positive dimensions.')
      }

      // Set ruleset if changed
      if (project && project.ruleset_id !== selectedRulesetId) {
        await api.setProjectRuleset(projectId, selectedRulesetId)
      }

      const updatedPlot = await api.setPlot(projectId, {
        width_mm: wMm,
        depth_mm: dMm,
        north_angle_deg: northAngle,
        road_sides: [{ edge_index: roadEdgeIndex, road_width_mm: roadMm }],
      })
      setPlot(updatedPlot)

      // Fetch newly computed envelope
      const envData = await api.getEnvelope(projectId)
      setEnvelope(envData)

      setToastMsg({ text: 'Plot geometry & buildable envelope calculated', type: 'success' })
    } catch (err: any) {
      setToastMsg({ text: err?.message || 'Failed to calculate envelope', type: 'error' })
    } finally {
      setUpdating(false)
    }
  }

  const handleRulesetChange = async (newRulesetId: string) => {
    setSelectedRulesetId(newRulesetId)
    try {
      await api.setProjectRuleset(projectId, newRulesetId)
      if (plot) {
        const envData = await api.getEnvelope(projectId)
        setEnvelope(envData)
      }
      setToastMsg({ text: `Ruleset updated to ${newRulesetId}`, type: 'success' })
    } catch (err: any) {
      setToastMsg({ text: err?.message || 'Failed to change ruleset', type: 'error' })
    }
  }

  const handleSearchRules = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    setSearching(true)
    try {
      const results = await api.searchRules(searchQuery.trim(), 5)
      setSearchResults(results)
    } catch (err: any) {
      setToastMsg({ text: err?.message || 'Search failed', type: 'error' })
    } finally {
      setSearching(false)
    }
  }

  // Calculate SVG ViewBox & Scale
  const plotCoords = plot?.boundary || [
    [0, 0],
    [parseFloat(widthMeters) * 1000 || 15000, 0],
    [parseFloat(widthMeters) * 1000 || 15000, parseFloat(depthMeters) * 1000 || 20000],
    [0, parseFloat(depthMeters) * 1000 || 20000],
    [0, 0],
  ]

  const xs = plotCoords.map((p) => p[0])
  const ys = plotCoords.map((p) => p[1])
  const minX = Math.min(...xs, 0)
  const maxX = Math.max(...xs, 15000)
  const minY = Math.min(...ys, 0)
  const maxY = Math.max(...ys, 20000)
  const plotW = maxX - minX || 15000
  const plotH = maxY - minY || 20000
  const padding = Math.max(plotW, plotH) * 0.15
  const viewBox = `${minX - padding} ${minY - padding} ${plotW + padding * 2} ${plotH + padding * 2}`

  const footprintCoords = envelope?.footprint_polygon || []
  const footprintSvgPath =
    footprintCoords.length > 0
      ? `M ${footprintCoords.map((p) => `${p[0]} ${p[1]}`).join(' L ')} Z`
      : ''
  const plotSvgPath = `M ${plotCoords.map((p) => `${p[0]} ${p[1]}`).join(' L ')} Z`

  if (loading && !project) {
    return (
      <AppShell currentTab="projects">
        <div className="flex items-center justify-center min-h-[400px]">
          <span className="font-mono text-xs uppercase text-[var(--ink-50)] animate-pulse">
            [ LOADING PROJECT DATA... ]
          </span>
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell currentTab="projects">
      <div className="flex flex-col gap-4 max-w-7xl w-full mx-auto pb-8">
        {/* Top Breadcrumb & Metadata Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--line)] gap-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <Link to="/projects" className="font-mono text-[11px] text-[var(--accent)] hover:underline">
              ← PROJECTS
            </Link>
            <span className="font-mono text-[11px] text-[var(--ink-50)]">/</span>
            <span className="font-sans font-bold text-base sm:text-lg uppercase text-[var(--ink)]">
              {project?.name || 'Project Envelope'}
            </span>
            <BracketLabel text="PHASE 02" />
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <div className="flex items-center gap-1.5 sm:gap-2">
              <label htmlFor="jurisdiction-select" className="font-mono text-[10.5px] sm:text-[11px] uppercase text-[var(--ink-50)]">
                Ruleset:
              </label>
              <select
                id="jurisdiction-select"
                aria-label="Governing Jurisdiction Ruleset"
                value={selectedRulesetId}
                onChange={(e) => handleRulesetChange(e.target.value)}
                className="font-mono text-[10.5px] sm:text-[11px] uppercase bg-[var(--paper)] text-[var(--ink)] border border-[var(--line)] px-1.5 sm:px-2 py-1 outline-none"
              >
                {rulesets.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.rule_count} rules)
                  </option>
                ))}
              </select>
            </div>
            {envelope && envelope.footprint_area_mm2 > 0 ? (
              <StatusPill status="pass" label="Envelope Valid" />
            ) : (
              <StatusPill status="review" label="Requires Definition" />
            )}
          </div>
        </div>

        {toastMsg && (
          <Toast message={toastMsg.text} type={toastMsg.type} onClose={() => setToastMsg(null)} />
        )}

        {/* Top-Level Architectural Workspace Switcher */}
        <div className="flex flex-wrap items-center gap-2 border-b border-[var(--line)] pb-2 mb-2">
          <button
            type="button"
            onClick={() => setActiveTab('generator')}
            className={`px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors ${
              activeTab === 'generator'
                ? 'bg-[var(--accent)] text-[var(--paper)] font-bold'
                : 'text-[var(--ink-72)] hover:bg-[var(--line-soft)]'
            }`}
          >
            [00] AI Brief & Generator
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('workspace')}
            className={`px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors ${
              activeTab === 'workspace'
                ? 'bg-[var(--ink)] text-[var(--paper)] font-bold'
                : 'text-[var(--ink-72)] hover:bg-[var(--line-soft)]'
            }`}
          >
            [01] 2D Plan Workspace & Review
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('envelope')}
            className={`px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors ${
              activeTab === 'envelope'
                ? 'bg-[var(--ink)] text-[var(--paper)] font-bold'
                : 'text-[var(--ink-72)] hover:bg-[var(--line-soft)]'
            }`}
          >
            [02] Site Plot & Buildable Envelope
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('rag')}
            className={`px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors ${
              activeTab === 'rag'
                ? 'bg-[var(--ink)] text-[var(--paper)] font-bold'
                : 'text-[var(--ink-72)] hover:bg-[var(--line-soft)]'
            }`}
          >
            [03] Statutory Rules & RAG Search ({envelope?.applied_rules.length || 0})
          </button>
        </div>

        {activeTab === 'generator' ? (
          <PlanGenerator
            projectId={projectId}
            envelope={envelope}
            onOpenInWorkspace={(planId) => {
              setWorkspacePlanId(planId)
              setActiveTab('workspace')
            }}
          />
        ) : activeTab === 'workspace' ? (
          <PlanWorkspace
            projectId={projectId}
            rulesetId={selectedRulesetId}
            envelope={envelope}
            initialPlanId={workspacePlanId}
          />
        ) : (
          /* Main Grid: Left Controls & Form | Right Spatial Drafting Workspace */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Left Configuration Panel (4 Cols) */}
            <div className="lg:col-span-4 flex flex-col gap-4">
              <Card title="Plot Parameters" subtitle="Define site geometry and setbacks" darkHeader>
              <form onSubmit={handleSavePlot} className="flex flex-col gap-3">
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    label="Width (m)"
                    type="number"
                    step="0.1"
                    min="2"
                    required
                    value={widthMeters}
                    onChange={(e) => setWidthMeters(e.target.value)}
                  />
                  <Input
                    label="Depth (m)"
                    type="number"
                    step="0.1"
                    min="2"
                    required
                    value={depthMeters}
                    onChange={(e) => setDepthMeters(e.target.value)}
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <Input
                    label="Road Width (m)"
                    type="number"
                    step="0.5"
                    min="3"
                    value={roadWidthMeters}
                    onChange={(e) => setRoadWidthMeters(e.target.value)}
                  />
                  <div className="flex flex-col gap-1 text-left">
                    <label htmlFor="road-facing-edge-select" className="font-mono text-[11px] uppercase tracking-wider text-[var(--ink-72)]">
                      Road Facing Side
                    </label>
                    <select
                      id="road-facing-edge-select"
                      aria-label="Road Facing Edge"
                      value={roadEdgeIndex}
                      onChange={(e) => setRoadEdgeIndex(parseInt(e.target.value, 10))}
                      className="h-10 px-2 font-mono text-[12px] bg-[var(--paper)] text-[var(--ink)] border border-[var(--line)] outline-none"
                    >
                      <option value={0}>Side 0 (Bottom / South)</option>
                      <option value={1}>Side 1 (Right / East)</option>
                      <option value={2}>Side 2 (Top / North)</option>
                      <option value={3}>Side 3 (Left / West)</option>
                    </select>
                  </div>
                </div>

                {/* North Arrow Slider */}
                <div className="flex flex-col gap-1 text-left pt-1">
                  <div className="flex items-center justify-between font-mono text-[11px] text-[var(--ink-72)]">
                    <label htmlFor="north-angle-range">North Orientation</label>
                    <span className="font-bold">{northAngle}°</span>
                  </div>
                  <input
                    id="north-angle-range"
                    aria-label="North Angle Degree"
                    type="range"
                    min="0"
                    max="360"
                    step="5"
                    value={northAngle}
                    onChange={(e) => setNorthAngle(parseInt(e.target.value, 10))}
                    className="w-full accent-[var(--accent)] cursor-pointer"
                  />
                </div>

                <div className="pt-2">
                  <Button
                    type="submit"
                    label={updating ? 'Computing Envelope...' : 'Recalculate Envelope →'}
                    variant="accent"
                    size="md"
                    className="w-full justify-center"
                  />
                </div>
              </form>

              {/* Area Readout Metrics */}
              <div className="mt-4 pt-3 border-t border-[var(--line)] flex flex-col gap-2 font-mono text-[11px]">
                <DataRow
                  label="Plot Area"
                  value={`${((plot?.plot_area_mm2 || parseFloat(widthMeters) * parseFloat(depthMeters) * 1e6) / 1e6).toFixed(1)} sqm`}
                  accent
                />
                <DataRow
                  label="Buildable Footprint"
                  value={
                    envelope
                      ? `${(envelope.footprint_area_mm2 / 1e6).toFixed(1)} sqm (${((envelope.footprint_area_mm2 / (plot?.plot_area_mm2 || 1)) * 100).toFixed(1)}%)`
                      : 'Not computed'
                  }
                />
                <DataRow
                  label="Max Total Built-up (FAR)"
                  value={
                    envelope
                      ? `${(envelope.max_builtup_mm2 / 1e6).toFixed(1)} sqm`
                      : 'Not computed'
                  }
                />
                <DataRow
                  label="Max Height / Floors"
                  value={
                    envelope
                      ? `${envelope.max_height_mm / 1000} m (G+${envelope.max_floors - 1})`
                      : 'Not computed'
                  }
                />
              </div>
            </Card>

            {/* Regulatory Rule Search / Explainer Box */}
            <Card title="Rule RAG Search" subtitle="Query official bylaws & clauses" darkHeader={false}>
              <form onSubmit={handleSearchRules} className="flex gap-2">
                <input
                  type="text"
                  placeholder="e.g. habitable room, setback..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="flex-1 h-9 px-2 font-mono text-[11px] bg-[var(--paper)] text-[var(--ink)] border border-[var(--line)] outline-none"
                />
                <button
                  type="submit"
                  disabled={searching}
                  className="px-3 h-9 bg-[var(--ink)] text-white font-mono text-[11px] uppercase hover:bg-[var(--accent)] transition-colors"
                >
                  {searching ? '...' : 'Search'}
                </button>
              </form>

              {searchResults.length > 0 && (
                <div className="mt-3 flex flex-col gap-2 max-h-60 overflow-y-auto">
                  {searchResults.map((res, i) => (
                    <div key={i} className="p-2 border border-[var(--line)] bg-[var(--paper-2)] text-left font-mono text-[10px]">
                      <div className="flex items-center justify-between font-bold text-[var(--ink)] mb-1">
                        <span>{res.section}</span>
                        <span className="text-[var(--ok)]">Score: {res.score}</span>
                      </div>
                      <p className="text-[var(--ink-72)] line-clamp-3">{res.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* Right Spatial Drafting Workspace (8 Cols) */}
          <div className="lg:col-span-8 flex flex-col gap-3">
            {/* View Mode Switcher */}
            <div className="flex items-center justify-between border-b border-[var(--line)] pb-2">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveTab('envelope')}
                  className={`px-3 py-1 font-mono text-[11px] uppercase transition-colors ${activeTab === 'envelope' ? 'bg-[var(--ink)] text-white' : 'text-[var(--ink-72)] hover:bg-[var(--paper-2)]'}`}
                >
                  [01] Spatial Envelope View
                </button>
                <button
                  onClick={() => setActiveTab('rag')}
                  className={`px-3 py-1 font-mono text-[11px] uppercase transition-colors ${activeTab === 'rag' ? 'bg-[var(--ink)] text-white' : 'text-[var(--ink-72)] hover:bg-[var(--paper-2)]'}`}
                >
                  [02] Applied Rule Constraints ({envelope?.applied_rules.length || 0})
                </button>
              </div>

              {/* Live Cursor Coordinate Readout */}
              <div className="hidden sm:flex items-center gap-2">
                <CoordLabel
                  axis="X"
                  value={hoverCoord ? hoverCoord.x : plotCoords[1][0]}
                  unit="MM"
                />
                <CoordLabel
                  axis="Y"
                  value={hoverCoord ? hoverCoord.y : plotCoords[2][1]}
                  unit="MM"
                />
              </div>
            </div>

            {activeTab === 'envelope' ? (
              /* Vector Drafting Canvas */
              <div
                className="relative w-full border border-[var(--line)] bg-[var(--paper)] flex items-center justify-center p-3 sm:p-6 overflow-hidden"
                style={{
                  minHeight: 'clamp(320px, 45vh, 520px)',
                  boxShadow: '0 4px 0 var(--ink)',
                  backgroundImage:
                    'radial-gradient(circle, var(--line-soft) 1px, transparent 1px)',
                  backgroundSize: '24px 24px',
                }}
              >
                {/* North Arrow Compass Indicator */}
                <div className="absolute top-4 right-4 flex flex-col items-center gap-1 z-10 bg-[var(--paper)] p-2 border border-[var(--line)] font-mono text-[10px]">
                  <div
                    className="w-8 h-8 flex items-center justify-center transition-transform duration-200"
                    style={{ transform: `rotate(${northAngle}deg)` }}
                  >
                    <svg viewBox="0 0 24 24" className="w-6 h-6 stroke-[var(--ink)] fill-none">
                      <polygon points="12 2 16 12 12 9 8 12 12 2" fill="var(--accent)" stroke="var(--accent)" />
                      <polygon points="12 22 16 12 12 15 8 12 12 22" fill="var(--ink-50)" stroke="var(--ink-50)" />
                    </svg>
                  </div>
                  <span className="font-bold text-[var(--accent)]">N</span>
                </div>

                {/* SVG Vector Plot & Envelope Canvas */}
                <svg
                  viewBox={viewBox}
                  className="w-full h-full max-h-[500px]"
                  style={{ transform: 'scaleY(-1)' }} // Invert Y so 0,0 is at bottom-left
                  onMouseMove={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect()
                    const relX = (e.clientX - rect.left) / rect.width
                    const relY = 1.0 - (e.clientY - rect.top) / rect.height
                    setHoverCoord({
                      x: Math.round(minX + relX * plotW),
                      y: Math.round(minY + relY * plotH),
                    })
                  }}
                  onMouseLeave={() => setHoverCoord(null)}
                >
                  <defs>
                    <pattern
                      id="draftingHatch"
                      width="1200"
                      height="1200"
                      patternUnits="userSpaceOnUse"
                      patternTransform="rotate(45)"
                    >
                      <line x1="0" y1="0" x2="0" y2="1200" stroke="var(--accent)" strokeWidth="80" strokeOpacity="0.25" />
                    </pattern>
                  </defs>

                  {/* 1. Plot Boundary Polygon */}
                  <path
                    d={plotSvgPath}
                    fill="var(--paper-2)"
                    stroke="var(--ink)"
                    strokeWidth="180"
                    strokeDasharray="400,200"
                  />

                  {/* 2. Road Facing Highlight Edge */}
                  {plotCoords.length >= 4 && (
                    <line
                      x1={plotCoords[roadEdgeIndex][0]}
                      y1={plotCoords[roadEdgeIndex][1]}
                      x2={plotCoords[(roadEdgeIndex + 1) % (plotCoords.length - 1)][0]}
                      y2={plotCoords[(roadEdgeIndex + 1) % (plotCoords.length - 1)][1]}
                      stroke="var(--accent)"
                      strokeWidth="350"
                    />
                  )}

                  {/* 3. Buildable Footprint Polygon */}
                  {footprintSvgPath && (
                    <g>
                      <path
                        d={footprintSvgPath}
                        fill="url(#draftingHatch)"
                        stroke="var(--accent)"
                        strokeWidth="240"
                      />
                    </g>
                  )}

                  {/* 4. Setback Guide Lines / Labels */}
                  {plotCoords.length >= 4 && footprintCoords.length >= 4 && (
                    <g opacity="0.6">
                      <line
                        x1={plotCoords[0][0]}
                        y1={footprintCoords[0][1]}
                        x2={plotCoords[1][0]}
                        y2={footprintCoords[0][1]}
                        stroke="var(--ink-50)"
                        strokeWidth="80"
                        strokeDasharray="200,200"
                      />
                    </g>
                  )}
                </svg>

                {/* Live Dimension Readouts Overlay */}
                <div className="absolute bottom-3 left-4 flex items-center gap-3 font-mono text-[10px] text-[var(--ink-72)] bg-[var(--paper)] px-3 py-1.5 border border-[var(--line)]">
                  <span>WIDTH: <strong>{plotW} MM</strong></span>
                  <span className="text-[var(--ink-30)]">|</span>
                  <span>DEPTH: <strong>{plotH} MM</strong></span>
                  <span className="text-[var(--ink-30)]">|</span>
                  <span>ROAD: <strong>{roadWidthMeters}M (SIDE {roadEdgeIndex})</strong></span>
                </div>

                {/* Legend */}
                <div className="absolute top-4 left-4 flex flex-col gap-1.5 font-mono text-[10px] bg-[var(--paper)] p-2.5 border border-[var(--line)]">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-0.5 border-t border-dashed border-[var(--ink)]" />
                    <span>Plot Boundary</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-1.5 bg-[var(--accent)] opacity-40 inline-block border border-[var(--accent)]" />
                    <span>Buildable Footprint</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-1 bg-[var(--accent)] inline-block" />
                    <span>Road Facing Edge</span>
                  </div>
                </div>
              </div>
            ) : (
              /* Applied Regulatory Rules & Clause Citations Table */
              <div className="flex flex-col gap-3">
                <div className="font-mono text-[11px] text-[var(--ink-72)] pb-1">
                  Every parameter enforced by the geometry engine traces directly to a cited legislative clause.
                </div>

                <div className="border border-[var(--line)] bg-[var(--paper)] overflow-hidden" style={{ boxShadow: '0 4px 0 var(--ink)' }}>
                  <div className="grid grid-cols-12 bg-[var(--ink)] text-white font-mono text-[11px] uppercase py-2 px-3">
                    <div className="col-span-3">Constraint Rule</div>
                    <div className="col-span-3">Legislative Clause</div>
                    <div className="col-span-3">Value / Threshold</div>
                    <div className="col-span-3 text-right">Verification Status</div>
                  </div>

                  <div className="divide-y divide-[var(--line)]">
                    {envelope?.applied_rules.map((rule, idx) => (
                      <div key={idx} className="grid grid-cols-12 font-mono text-[11px] py-2.5 px-3 items-center hover:bg-[var(--paper-2)]">
                        <div className="col-span-3 font-semibold uppercase text-[var(--ink)]">
                          {rule.rule_id}
                        </div>
                        <div className="col-span-3 text-[var(--ink-72)]">
                          {rule.clause}
                        </div>
                        <div className="col-span-3 text-[var(--accent)] font-bold">
                          {rule.value}
                        </div>
                        <div className="col-span-3 flex justify-end">
                          {rule.verified ? (
                            <StatusPill status="pass" label="Pass · Verified" />
                          ) : (
                            <StatusPill status="review" label="Review · Unverified" />
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  </AppShell>
)
}
