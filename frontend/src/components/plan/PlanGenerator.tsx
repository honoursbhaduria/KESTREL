import { useEffect, useState } from 'react'
import {
  api,
  type BriefProgramResponse,
  type Envelope,
  type GeneratedOptionItem,
} from '~/api/client'
import { Button } from '~/components/shared/Button'
import { Card } from '~/components/shared/Card'
import { StatusPill } from '~/components/shared/StatusPill'
import { Modal } from '~/components/shared/Modal'

interface PlanGeneratorProps {
  projectId: string
  envelope: Envelope | null
  onOpenInWorkspace: (planId?: string) => void
}

const PRESET_BRIEFS = [
  {
    label: '3BHK 2-Storey Vastu Villa',
    text: 'Design a 2-storey 3BHK house. Ground floor: living room, open modular kitchen, dining, pooja room, guest bedroom with attached bath, powder toilet, stair. First floor: master bedroom with walk-in closet and bath, kids bedroom with bath, family lounge. East-facing entrance, Vastu compliant, front parking.',
  },
  {
    label: 'Compact 2BHK Single-Floor',
    text: 'Compact 2BHK 1 floor house, living room, open kitchen, 2 bedrooms, 1 bathroom. East entrance, vastu preferred.',
  },
  {
    label: 'Luxury 4BHK Courtyard House',
    text: 'Spacious 4BHK residence with central living foyer, formal dining, chef kitchen with utility, ground guest suite, 3 upper bedrooms with attached baths, dedicated home office, north entrance.',
  },
]

export function PlanGenerator({ projectId, envelope, onOpenInWorkspace }: PlanGeneratorProps) {
  const [briefText, setBriefText] = useState(PRESET_BRIEFS[0].text)
  const [structuring, setStructuring] = useState(false)
  const [programData, setProgramData] = useState<BriefProgramResponse | null>(null)
  const [options, setOptions] = useState<GeneratedOptionItem[]>([])
  const [loadingOptions, setLoadingOptions] = useState(false)

  // Generation Job State
  const [generating, setGenerating] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobProgress, setJobProgress] = useState(0)
  const [jobPhase, setJobPhase] = useState<'indexing' | 'zoning' | 'placing' | 'checking'>('indexing')

  // Comparison State
  const [compareModalOpen, setCompareModalOpen] = useState(false)
  const [compareSchemes, setCompareSchemes] = useState<[GeneratedOptionItem, GeneratedOptionItem] | null>(null)

  // Load existing program and options on mount
  useEffect(() => {
    loadExistingProgram()
    loadOptions()
  }, [projectId])

  const loadExistingProgram = async () => {
    try {
      const res = await api.getProjectProgram(projectId)
      if (res && res.program && res.program.rooms && res.program.rooms.length > 0) {
        setProgramData(res)
        if (res.brief_text) {
          setBriefText(res.brief_text)
        }
      }
    } catch (e) {
      console.warn('No existing program found', e)
    }
  }

  const loadOptions = async () => {
    try {
      setLoadingOptions(true)
      const res = await api.listGeneratedOptions(projectId)
      setOptions(res.options || [])
    } catch (e) {
      console.error('Failed to load generated options', e)
    } finally {
      setLoadingOptions(false)
    }
  }

  const handleStructureBrief = async () => {
    if (!briefText.trim()) return
    try {
      setStructuring(true)
      const res = await api.setProjectBrief(projectId, briefText)
      setProgramData(res)
    } catch (e) {
      console.error('Failed to structure brief', e)
    } finally {
      setStructuring(false)
    }
  }

  const handleApplySuggestedProgram = async () => {
    if (!programData?.feasibility?.suggested_program) return
    try {
      setStructuring(true)
      const res = await api.setProjectProgram(projectId, programData.feasibility.suggested_program)
      setProgramData(res)
    } catch (e) {
      console.error('Failed to apply suggested program', e)
    } finally {
      setStructuring(false)
    }
  }

  const handleStartGeneration = async () => {
    try {
      setGenerating(true)
      setJobProgress(10)
      setJobPhase('indexing')

      const jobResp = await api.generatePlans(projectId, 3, Date.now() % 100000)
      setJobId(jobResp.job_id)

      // Poll job progress
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await api.getJob(jobResp.job_id)
          const prog = statusRes.progress || 0
          setJobProgress(prog)

          if (prog < 30) setJobPhase('indexing')
          else if (prog < 60) setJobPhase('zoning')
          else if (prog < 85) setJobPhase('placing')
          else setJobPhase('checking')

          if (statusRes.status === 'done' || statusRes.status === 'failed' || prog >= 100) {
            clearInterval(pollInterval)
            setGenerating(false)
            setJobId(null)
            await loadOptions()
          }
        } catch (err) {
          clearInterval(pollInterval)
          setGenerating(false)
        }
      }, 400)
    } catch (e) {
      console.error('Generation failed to trigger', e)
      setGenerating(false)
    }
  }

  const handleOpenCompare = (schemeA: GeneratedOptionItem, schemeB: GeneratedOptionItem) => {
    setCompareSchemes([schemeA, schemeB])
    setCompareModalOpen(true)
  }

  const currentProgram = programData?.program
  const feasibility = programData?.feasibility

  return (
    <div className="flex flex-col gap-6">
      {/* 1. Brief Input & Quick Presets */}
      <Card
        title="[01] Architectural Client Brief"
        subtitle="Natural language requirements parsed into a statutory design program"
        darkHeader
      >
        <div className="flex flex-col gap-3 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[10px] uppercase text-[var(--ink-72)]">Quick Starters:</span>
            {PRESET_BRIEFS.map((preset) => (
              <button
                key={preset.label}
                type="button"
                onClick={() => setBriefText(preset.text)}
                className="px-2 py-1 font-mono text-[10px] border border-[var(--line)] bg-[var(--paper-soft)] hover:bg-[var(--line-soft)] text-[var(--ink)] transition-colors"
              >
                {preset.label}
              </button>
            ))}
          </div>

          <textarea
            value={briefText}
            onChange={(e) => setBriefText(e.target.value)}
            rows={4}
            placeholder="Describe your architectural program in plain language..."
            className="w-full p-3 font-mono text-xs border border-[var(--line)] bg-[var(--paper)] text-[var(--ink)] focus:outline-none focus:border-[var(--accent)] resize-y leading-relaxed"
          />

          <div className="flex items-center justify-between pt-2 border-t border-[var(--line)]">
            <span className="font-mono text-[10px] text-[var(--ink-72)]">
              {briefText.length} characters · LLM parses functional zones, code bounds & Vastu
            </span>
            <Button
              label={structuring ? 'Structuring Brief...' : 'Structure Brief → Program'}
              onClick={handleStructureBrief}
              variant="accent"
              icon="arrow"
            />
          </div>
        </div>
      </Card>

      {/* 2. Structured Program Table & Statutory Feasibility */}
      {currentProgram && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* Left: Program Table (8 Cols) */}
          <div className="lg:col-span-8">
            <Card
              title={`[02] Structured Architectural Program (${currentProgram.rooms.length} Spaces)`}
              subtitle={`${currentProgram.levels} Above-ground Floors · Entrance: ${currentProgram.preferences.entrance_side.toUpperCase()} · Vastu: ${currentProgram.preferences.vastu ? 'Enabled' : 'Disabled'}`}
              darkHeader
            >
              <div className="p-3 overflow-x-auto">
                <table className="w-full text-left font-mono text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[var(--line)] text-[10px] uppercase text-[var(--ink-72)]">
                      <th className="py-2 px-2">Room Designation</th>
                      <th className="py-2 px-2">Type</th>
                      <th className="py-2 px-2 text-right">Target Area</th>
                      <th className="py-2 px-2 text-right">Min Width</th>
                      <th className="py-2 px-2 text-center">Level</th>
                      <th className="py-2 px-2 text-center">Ext. Wall</th>
                      <th className="py-2 px-2 text-center">En-Suite</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentProgram.rooms.map((room, idx) => (
                      <tr key={`${room.name}-${idx}`} className="border-b border-[var(--line-soft)] hover:bg-[var(--line-soft)]/40 transition-colors">
                        <td className="py-2 px-2 font-medium text-[var(--ink)]">{room.name}</td>
                        <td className="py-2 px-2 text-[var(--ink-72)] uppercase text-[10px]">{room.type}</td>
                        <td className="py-2 px-2 text-right font-bold text-[var(--ink)]">
                          {(room.target_area_mm2 / 1e6).toFixed(1)} m²
                        </td>
                        <td className="py-2 px-2 text-right text-[var(--ink-72)]">
                          {(room.min_width_mm / 1000).toFixed(1)} m
                        </td>
                        <td className="py-2 px-2 text-center font-bold">
                          L{room.level_hint}
                        </td>
                        <td className="py-2 px-2 text-center">
                          {room.needs_exterior_wall ? (
                            <span className="text-[var(--accent)] font-bold">✓</span>
                          ) : (
                            <span className="text-[var(--ink-72)]">—</span>
                          )}
                        </td>
                        <td className="py-2 px-2 text-center">
                          {room.needs_attached_bath ? (
                            <span className="text-[var(--accent)] font-bold">✓</span>
                          ) : (
                            <span className="text-[var(--ink-72)]">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          {/* Right: Statutory Feasibility Inspector (4 Cols) */}
          <div className="lg:col-span-4 flex flex-col gap-4">
            <Card title="[03] Statutory Feasibility" subtitle="Envelope verification before layout generation" darkHeader>
              <div className="p-4 flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-medium text-[var(--ink)]">Legal Status:</span>
                  {feasibility?.is_feasible ? (
                    <StatusPill status="pass" label="Statutory Compliant" />
                  ) : (
                    <StatusPill status="fail" label="FAR / Area Exceeded" />
                  )}
                </div>

                {/* Built-Up Area Gauge */}
                <div className="flex flex-col gap-1 border-t border-[var(--line)] pt-3">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-[var(--ink-72)]">Proposed Built-Up:</span>
                    <span className="font-bold text-[var(--ink)]">
                      {feasibility?.total_proposed_area_sqm || 0} m²
                    </span>
                  </div>
                  <div className="flex justify-between text-[11px] font-mono text-[var(--ink-72)]">
                    <span>Permissible FAR Cap:</span>
                    <span>{feasibility?.max_builtup_area_sqm || 0} m²</span>
                  </div>
                  <div className="w-full bg-[var(--line-soft)] h-2 rounded-full overflow-hidden mt-1">
                    <div
                      className={`h-full transition-all ${
                        (feasibility?.total_proposed_area_sqm || 0) > (feasibility?.max_builtup_area_sqm || 1)
                          ? 'bg-red-500'
                          : 'bg-[var(--accent)]'
                      }`}
                      style={{
                        width: `${Math.min(
                          100,
                          ((feasibility?.total_proposed_area_sqm || 0) /
                            Math.max(1, feasibility?.max_builtup_area_sqm || 100)) *
                            100
                        )}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Ground Coverage Gauge */}
                <div className="flex flex-col gap-1">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-[var(--ink-72)]">Ground Floor Footprint:</span>
                    <span className="font-bold text-[var(--ink)]">
                      {feasibility?.ground_coverage_sqm || 0} m²
                    </span>
                  </div>
                  <div className="flex justify-between text-[11px] font-mono text-[var(--ink-72)]">
                    <span>Max Ground Coverage:</span>
                    <span>{feasibility?.max_coverage_sqm || 0} m²</span>
                  </div>
                </div>

                {/* Infeasibility Callout & Adjustment */}
                {feasibility && !feasibility.is_feasible && (
                  <div className="p-3 bg-red-500/10 border border-red-500/30 flex flex-col gap-2">
                    <div className="flex items-center gap-2 text-red-600 font-bold font-mono text-xs">
                      <span>⚠</span>
                      <span>Statutory Violation Detected</span>
                    </div>
                    <p className="font-mono text-[11px] text-[var(--ink)] leading-relaxed">
                      {feasibility.explanation}
                    </p>
                    {feasibility.suggested_program && (
                      <button
                        type="button"
                        onClick={handleApplySuggestedProgram}
                        className="mt-1 px-3 py-1.5 bg-[var(--ink)] text-[var(--paper)] font-mono text-xs font-bold hover:bg-[var(--accent)] transition-colors"
                      >
                        Scale Program to Legal Max FAR →
                      </button>
                    )}
                  </div>
                )}

                {/* Generate Button */}
                <div className="pt-2 border-t border-[var(--line)]">
                  <Button
                    label={generating ? 'Synthesizing Layouts...' : 'Generate 3 Code-Checked Schemes →'}
                    onClick={handleStartGeneration}
                    variant="accent"
                    icon="arrow"
                  />
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* 3. Generation Progress Modal (Landing Page Style) */}
      <Modal
        isOpen={generating}
        title={`GENERATIVE LAYOUT ENGINE — REAL-TIME SYNTHESIS ${jobId ? `[JOB: ${jobId.slice(0, 8)}]` : ''}`}
        onClose={() => setGenerating(false)}
      >
        <div className="flex flex-col gap-6 p-4">
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between font-mono text-xs">
              <span className="font-bold uppercase tracking-wider text-[var(--ink)]">
                Phase: {jobPhase.toUpperCase()}
              </span>
              <span className="font-bold text-[var(--accent)]">{jobProgress}%</span>
            </div>
            <div className="w-full bg-[var(--line-soft)] h-2 rounded-full overflow-hidden">
              <div
                className="bg-[var(--accent)] h-full transition-all duration-300"
                style={{ width: `${jobProgress}%` }}
              />
            </div>
          </div>

          {/* 4 Architectural Progress Cards */}
          <div className="grid grid-cols-2 gap-3 font-mono text-xs">
            <div
              className={`p-3 border transition-colors ${
                jobPhase === 'indexing'
                  ? 'border-[var(--accent)] bg-[var(--accent)]/5'
                  : 'border-[var(--line)] bg-[var(--paper)]'
              }`}
            >
              <div className="text-[10px] text-[var(--ink-72)] uppercase">[01] INDEXING</div>
              <div className="font-bold mt-1">Footprint & Envelope</div>
              <div className="text-[10px] text-[var(--ink-72)] mt-1">Reading site polygon & setbacks</div>
            </div>

            <div
              className={`p-3 border transition-colors ${
                jobPhase === 'zoning'
                  ? 'border-[var(--accent)] bg-[var(--accent)]/5'
                  : 'border-[var(--line)] bg-[var(--paper)]'
              }`}
            >
              <div className="text-[10px] text-[var(--ink-72)] uppercase">[02] ZONING</div>
              <div className="font-bold mt-1">Topological Partition</div>
              <div className="text-[10px] text-[var(--ink-72)] mt-1">Public vs Private vs Stair Core</div>
            </div>

            <div
              className={`p-3 border transition-colors ${
                jobPhase === 'placing'
                  ? 'border-[var(--accent)] bg-[var(--accent)]/5'
                  : 'border-[var(--line)] bg-[var(--paper)]'
              }`}
            >
              <div className="text-[10px] text-[var(--ink-72)] uppercase">[03] PLACING</div>
              <div className="font-bold mt-1">Slicing Tree Solver</div>
              <div className="text-[10px] text-[var(--ink-72)] mt-1">Subdividing walls, doors, windows</div>
            </div>

            <div
              className={`p-3 border transition-colors ${
                jobPhase === 'checking'
                  ? 'border-[var(--accent)] bg-[var(--accent)]/5'
                  : 'border-[var(--line)] bg-[var(--paper)]'
              }`}
            >
              <div className="text-[10px] text-[var(--ink-72)] uppercase">[04] CHECKING</div>
              <div className="font-bold mt-1">Bylaws & AI Commentary</div>
              <div className="text-[10px] text-[var(--ink-72)] mt-1">Running NBC review & scoring</div>
            </div>
          </div>
        </div>
      </Modal>

      {/* 4. Generated Options Gallery */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-[var(--line)] pb-2">
          <div>
            <h2 className="font-mono text-sm font-bold uppercase tracking-wider text-[var(--ink)]">
              [04] Generated Layout Schemes ({options.length} Options)
            </h2>
            <p className="font-mono text-xs text-[var(--ink-72)]">
              Deterministic geometry synthesized from program weights, Vastu quadrants, and statutory setback limits
            </p>
          </div>
          {options.length >= 2 && (
            <button
              type="button"
              onClick={() => handleOpenCompare(options[0], options[1])}
              className="px-3 py-1.5 font-mono text-xs border border-[var(--ink)] hover:bg-[var(--ink)] hover:text-[var(--paper)] transition-colors"
            >
              Compare Schemes A & B Side-by-Side ⇄
            </button>
          )}
        </div>

        {loadingOptions ? (
          <div className="p-8 text-center font-mono text-xs text-[var(--ink-72)]">
            Loading generated options...
          </div>
        ) : options.length === 0 ? (
          <div className="p-12 text-center border border-dashed border-[var(--line)] font-mono text-xs text-[var(--ink-72)] flex flex-col items-center gap-2">
            <span>No generated options yet.</span>
            <span>Type a brief above and click "Generate 3 Code-Checked Schemes" to synthesize floor plans.</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {options.map((opt, i) => (
              <div
                key={opt.id}
                className="flex flex-col border border-[var(--line)] bg-[var(--paper)] hover:border-[var(--ink)] transition-all shadow-sm"
              >
                {/* Card Header */}
                <div className="p-3 bg-[var(--ink)] text-[var(--paper)] flex items-center justify-between">
                  <span className="font-mono text-xs font-bold uppercase tracking-wider">
                    {opt.name}
                  </span>
                  <span className="px-2 py-0.5 bg-[var(--accent)] text-[var(--paper)] font-mono text-[11px] font-bold">
                    {opt.score_breakdown?.total_score || 85} PTS
                  </span>
                </div>

                {/* Mini SVG Plan Preview */}
                <div className="p-3 bg-[#f3f2ee] border-b border-[var(--line)] flex items-center justify-center min-h-[220px]">
                  {opt.data?.levels && opt.data.levels[0] ? (
                    <MiniPlanSVG level={opt.data.levels[0]} />
                  ) : (
                    <span className="font-mono text-xs text-[var(--ink-72)]">Drafting Preview</span>
                  )}
                </div>

                {/* Score Breakdown Metrics */}
                <div className="p-3 grid grid-cols-3 gap-2 border-b border-[var(--line)] text-center font-mono text-[10px]">
                  <div className="p-1.5 bg-[var(--paper-soft)] border border-[var(--line)]">
                    <div className="text-[var(--ink-72)] uppercase">Area Acc.</div>
                    <div className="font-bold text-[var(--ink)] mt-0.5">
                      {opt.score_breakdown?.area_score || 90}%
                    </div>
                  </div>
                  <div className="p-1.5 bg-[var(--paper-soft)] border border-[var(--line)]">
                    <div className="text-[var(--ink-72)] uppercase">Vastu</div>
                    <div className="font-bold text-[var(--ink)] mt-0.5">
                      {opt.score_breakdown?.vastu_score || 85}%
                    </div>
                  </div>
                  <div className="p-1.5 bg-[var(--paper-soft)] border border-[var(--line)]">
                    <div className="text-[var(--ink-72)] uppercase">Daylight</div>
                    <div className="font-bold text-[var(--ink)] mt-0.5">
                      {opt.score_breakdown?.exterior_wall_score || 100}%
                    </div>
                  </div>
                </div>

                {/* Statutory Issue Summary */}
                <div className="px-3 py-2 border-b border-[var(--line)] flex items-center justify-between text-xs font-mono">
                  <span className="text-[var(--ink-72)]">Statutory Review:</span>
                  <div className="flex gap-2">
                    <span className="text-green-700 font-bold">
                      {opt.review_summary.passes} Pass
                    </span>
                    <span className="text-amber-600 font-medium">
                      {opt.review_summary.reviews} Review
                    </span>
                    <span className="text-red-600 font-bold">
                      {opt.review_summary.fails} Fail
                    </span>
                  </div>
                </div>

                {/* AI Commentary / Description */}
                <div className="p-3 text-xs font-mono text-[var(--ink-72)] leading-relaxed flex-1">
                  {opt.description || 'Optimized layout conforming to NBC 2016 room standards and setback guidelines.'}
                </div>

                {/* Open in Workspace Action */}
                <div className="p-3 border-t border-[var(--line)] bg-[var(--paper-soft)]">
                  <button
                    type="button"
                    onClick={() => onOpenInWorkspace(opt.id)}
                    className="w-full py-2 bg-[var(--ink)] hover:bg-[var(--accent)] text-[var(--paper)] font-mono text-xs font-bold uppercase tracking-wider transition-colors"
                  >
                    Open in 2D Workspace →
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 5. Compare Schemes Side-by-Side Modal */}
      {compareSchemes && (
        <Modal
          isOpen={compareModalOpen}
          title={`SIDE-BY-SIDE SCHEME COMPARISON: ${compareSchemes[0].name} vs ${compareSchemes[1].name}`}
          onClose={() => setCompareModalOpen(false)}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 font-mono text-xs">
            {compareSchemes.map((scheme, idx) => (
              <div key={scheme.id} className="flex flex-col border border-[var(--line)] bg-[var(--paper)]">
                <div className="p-2 bg-[var(--ink)] text-[var(--paper)] font-bold uppercase flex justify-between">
                  <span>{scheme.name}</span>
                  <span>{scheme.score_breakdown?.total_score} PTS</span>
                </div>
                <div className="p-4 bg-[#f3f2ee] min-h-[260px] flex items-center justify-center border-b border-[var(--line)]">
                  {scheme.data?.levels && scheme.data.levels[0] && (
                    <MiniPlanSVG level={scheme.data.levels[0]} />
                  )}
                </div>
                <div className="p-3 flex flex-col gap-2">
                  <div className="font-bold text-[var(--ink)]">Performance Metrics:</div>
                  <div className="grid grid-cols-2 gap-1 text-[11px]">
                    <span className="text-[var(--ink-72)]">Area Accuracy:</span>
                    <span className="font-bold">{scheme.score_breakdown?.area_score}%</span>
                    <span className="text-[var(--ink-72)]">Adjacency Satisfaction:</span>
                    <span className="font-bold">{scheme.score_breakdown?.adjacency_score}%</span>
                    <span className="text-[var(--ink-72)]">Vastu Compliance:</span>
                    <span className="font-bold">{scheme.score_breakdown?.vastu_score}%</span>
                    <span className="text-[var(--ink-72)]">Daylight Exposure:</span>
                    <span className="font-bold">{scheme.score_breakdown?.exterior_wall_score}%</span>
                  </div>
                  <p className="mt-2 text-[11px] text-[var(--ink-72)] leading-relaxed">
                    {scheme.description}
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setCompareModalOpen(false)
                      onOpenInWorkspace(scheme.id)
                    }}
                    className="mt-2 py-2 bg-[var(--ink)] hover:bg-[var(--accent)] text-[var(--paper)] font-bold uppercase transition-colors"
                  >
                    Select this Scheme →
                  </button>
                </div>
              </div>
            ))}
          </div>
        </Modal>
      )}
    </div>
  )
}

/**
 * Lightweight SVG Plan Preview Renderer for Option Cards
 */
function MiniPlanSVG({ level }: { level: any }) {
  const rooms = level.rooms || []
  const walls = level.walls || []

  // Compute bounding box
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  for (const r of rooms) {
    for (const [x, y] of r.polygon) {
      if (x < minX) minX = x
      if (y < minY) minY = y
      if (x > maxX) maxX = x
      if (y > maxY) maxY = y
    }
  }

  if (minX === Infinity) {
    return <span className="font-mono text-[10px] text-[var(--ink-72)]">Empty Plan</span>
  }

  const width = Math.max(100, maxX - minX)
  const height = Math.max(100, maxY - minY)
  const padding = 600

  return (
    <svg
      viewBox={`${minX - padding} ${minY - padding} ${width + padding * 2} ${height + padding * 2}`}
      className="w-full h-48 select-none"
    >
      {/* Rooms Polygons */}
      {rooms.map((rm: any, i: number) => {
        const points = rm.polygon.map(([x, y]: [number, number]) => `${x},${y}`).join(' ')
        // Color based on room type
        let fill = '#ffffff'
        if (rm.type === 'living') fill = '#eef3fb'
        else if (rm.type === 'kitchen') fill = '#fcf2ea'
        else if (rm.type === 'bedroom') fill = '#f0f7f2'
        else if (rm.type === 'bathroom') fill = '#f5f0fa'
        else if (rm.type === 'stair') fill = '#edebe6'

        // Centroid for label
        const cx = rm.polygon.reduce((acc: number, p: number[]) => acc + p[0], 0) / rm.polygon.length
        const cy = rm.polygon.reduce((acc: number, p: number[]) => acc + p[1], 0) / rm.polygon.length

        return (
          <g key={rm.id || i}>
            <polygon
              points={points}
              fill={fill}
              stroke="#282828"
              strokeWidth="40"
              strokeDasharray="20,20"
            />
            <text
              x={cx}
              y={cy}
              fontSize="450"
              fontFamily="monospace"
              fontWeight="bold"
              fill="#282828"
              textAnchor="middle"
              dominantBaseline="middle"
            >
              {rm.name}
            </text>
          </g>
        )
      })}

      {/* Walls */}
      {walls.map((w: any, idx: number) => (
        <line
          key={w.id || idx}
          x1={w.start[0]}
          y1={w.start[1]}
          x2={w.end[0]}
          y2={w.end[1]}
          stroke="#282828"
          strokeWidth={w.is_external ? 180 : 120}
          strokeLinecap="square"
        />
      ))}
    </svg>
  )
}
