import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import {
  api,
  type Envelope,
  type Issue,
  type Level,
  type Plan,
  type PlanData,
  type PlanVersion,
  type ReviewResult,
} from '~/api/client'
import { FIXTURE_2BHK, FIXTURE_OPTIONS } from '~/content/planFixtures'
import { Button } from '~/components/shared/Button'
import { Card } from '~/components/shared/Card'
import { BracketLabel, CoordLabel } from '~/components/shared/CoordLabel'
import { DataRow } from '~/components/shared/DataRow'
import { Input } from '~/components/shared/Input'
import { StatusPill } from '~/components/shared/StatusPill'
import { Toast } from '~/components/shared/Toast'

interface PlanWorkspaceProps {
  projectId: string
  rulesetId?: string
  envelope?: Envelope | null
}

export const PlanWorkspace: React.FC<PlanWorkspaceProps> = ({
  projectId,
  rulesetId,
  envelope,
}) => {
  const [plan, setPlan] = useState<Plan | null>(null)
  const [currentLevelIdx, setCurrentLevelIdx] = useState(0)
  const [selectedElement, setSelectedElement] = useState<{
    type: 'wall' | 'room' | 'opening' | 'stair'
    id: string
  } | null>(null)
  const [highlightedElementIds, setHighlightedElementIds] = useState<string[]>([])
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null)
  const [reviewFilter, setReviewFilter] = useState<'all' | 'fail' | 'review' | 'pass'>('all')
  const [showDimensions, setShowDimensions] = useState(true)
  const [showVersionsDrawer, setShowVersionsDrawer] = useState(false)
  const [versions, setVersions] = useState<PlanVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [reviewing, setReviewing] = useState(false)
  const [patching, setPatching] = useState(false)
  const [toastMsg, setToastMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  // Canvas Pan & Zoom
  const [zoom, setZoom] = useState(1.0)
  const [pan, setPan] = useState({ x: 100, y: 70 })
  const [isPanning, setIsPanning] = useState(false)
  const [panStart, setPanStart] = useState({ x: 0, y: 0 })
  const [cursorMm, setCursorMm] = useState<{ x: number; y: number } | null>(null)

  // Wall Dragging State
  const [draggingWallId, setDraggingWallId] = useState<string | null>(null)
  const [dragStartPos, setDragStartPos] = useState<{ x: number; y: number } | null>(null)
  const [dragCurrentDelta, setDragCurrentDelta] = useState<{ dx: number; dy: number }>({ dx: 0, dy: 0 })

  // Properties form state
  const [propWallThickness, setPropWallThickness] = useState('')
  const [propRoomName, setPropRoomName] = useState('')
  const [propRoomType, setPropRoomType] = useState('')
  const [propOpeningWidth, setPropOpeningWidth] = useState('')
  const [propOpeningOffset, setPropOpeningOffset] = useState('')

  const svgRef = useRef<SVGSVGElement | null>(null)

  // Load or initialize plan
  const loadPlan = useCallback(async () => {
    try {
      setLoading(true)
      try {
        const storedPlan = await api.getPlan(projectId)
        setPlan(storedPlan)
      } catch {
        const newPlan = await api.createPlan(projectId, {
          name: 'Primary Floor Scheme',
          data: FIXTURE_2BHK,
          message: 'Initial project plan scheme',
        })
        setPlan(newPlan)
      }
    } catch {
      setPlan({
        id: 'local-plan',
        project_id: projectId,
        name: 'Primary Floor Scheme (Local)',
        current_version: 1,
        data: FIXTURE_2BHK,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadPlan()
  }, [loadPlan])

  // Active level
  const activeLevel: Level | undefined = useMemo(() => {
    if (!plan || !plan.data.levels.length) return undefined
    return plan.data.levels[currentLevelIdx] || plan.data.levels[0]
  }, [plan, currentLevelIdx])

  // Sync properties form when selection changes
  useEffect(() => {
    if (!selectedElement || !activeLevel) return

    if (selectedElement.type === 'wall') {
      const w = activeLevel.walls.find((item) => item.id === selectedElement.id)
      if (w) setPropWallThickness(w.thickness_mm.toString())
    } else if (selectedElement.type === 'room') {
      const r = activeLevel.rooms.find((item) => item.id === selectedElement.id)
      if (r) {
        setPropRoomName(r.name)
        setPropRoomType(r.type)
      }
    } else if (selectedElement.type === 'opening') {
      const o = activeLevel.openings.find((item) => item.id === selectedElement.id)
      if (o) {
        setPropOpeningWidth(o.width_mm.toString())
        setPropOpeningOffset(o.offset_mm.toString())
      }
    }
  }, [selectedElement, activeLevel])

  // Run statutory review
  const handleRunReview = async () => {
    if (!plan) return
    try {
      setReviewing(true)
      const res = await api.reviewPlan(plan.id, rulesetId)
      setReviewResult(res)
      setToastMsg({
        text: `Review complete: ${res.summary.fail_count} fail, ${res.summary.review_count} review, ${res.summary.pass_count} pass.`,
        type: res.summary.fail_count > 0 ? 'error' : 'success',
      })
    } catch (err: any) {
      setToastMsg({ text: err?.message || 'Failed to run statutory review', type: 'error' })
    } finally {
      setReviewing(false)
    }
  }

  // Load Fixture Scheme
  const handleImportFixture = async (fixtureData: PlanData, schemeName: string) => {
    if (!plan) return
    try {
      setPatching(true)
      const updated = await api.createPlan(projectId, {
        name: schemeName,
        data: fixtureData,
        message: `Switched scheme to ${schemeName}`,
      })
      setPlan(updated)
      setSelectedElement(null)
      setHighlightedElementIds([])
      setReviewResult(null)
      setToastMsg({ text: `Loaded scheme: ${schemeName}`, type: 'success' })
    } catch {
      setPlan({
        ...plan,
        current_version: plan.current_version + 1,
        data: fixtureData,
      })
      setToastMsg({ text: `Switched scheme to ${schemeName}`, type: 'success' })
    } finally {
      setPatching(false)
    }
  }

  // Undo / Redo
  const handleUndo = async () => {
    if (!plan || plan.current_version <= 1) return
    try {
      const reverted = await api.undoPlan(plan.id)
      setPlan(reverted)
      setToastMsg({ text: `Reverted to version ${reverted.current_version}`, type: 'success' })
    } catch (err: any) {
      setToastMsg({ text: err?.message || 'Undo failed', type: 'error' })
    }
  }

  const handleRedo = async () => {
    if (!plan) return
    try {
      const advanced = await api.redoPlan(plan.id)
      setPlan(advanced)
      setToastMsg({ text: `Advanced to version ${advanced.current_version}`, type: 'success' })
    } catch (err: any) {
      setToastMsg({ text: err?.message || 'Redo failed', type: 'error' })
    }
  }

  // Keyboard Shortcuts (Cmd+Z / Ctrl+Z)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
        e.preventDefault()
        if (e.shiftKey) {
          handleRedo()
        } else {
          handleUndo()
        }
      } else if ((e.metaKey || e.ctrlKey) && e.key === 'y') {
        e.preventDefault()
        handleRedo()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [plan])

  // Load Version History Drawer
  const handleOpenHistory = async () => {
    if (!plan) return
    setShowVersionsDrawer(true)
    try {
      const vers = await api.listPlanVersions(plan.id)
      setVersions(vers)
    } catch {
      setVersions([])
    }
  }

  // Apply Wall Thickness Edit
  const handleSaveWallThickness = async () => {
    if (!plan || !selectedElement || selectedElement.type !== 'wall') return
    const thickness = parseFloat(propWallThickness)
    if (isNaN(thickness) || thickness <= 0) return

    try {
      setPatching(true)
      const updated = await api.applyPatches(plan.id, {
        message: `Set wall ${selectedElement.id} thickness to ${thickness}mm`,
        patches: [
          {
            type: 'set_wall_thickness',
            wall_id: selectedElement.id,
            thickness_mm: thickness,
          },
        ],
      })
      setPlan(updated)
      setToastMsg({ text: `Wall thickness updated to ${thickness} mm (v${updated.current_version})`, type: 'success' })
    } catch (err: any) {
      setToastMsg({ text: err?.message || 'Failed to update wall thickness', type: 'error' })
    } finally {
      setPatching(false)
    }
  }

  // Apply Room Name / Type Edit
  const handleSaveRoomProperties = async () => {
    if (!plan || !selectedElement || selectedElement.type !== 'room') return
    const patches: any[] = []
    if (propRoomName) {
      patches.push({
        type: 'rename_room',
        room_id: selectedElement.id,
        new_name: propRoomName,
      })
    }
    if (propRoomType) {
      patches.push({
        type: 'set_room_type',
        room_id: selectedElement.id,
        new_type: propRoomType,
      })
    }
    if (!patches.length) return

    try {
      setPatching(true)
      const updated = await api.applyPatches(plan.id, {
        message: `Updated room ${selectedElement.id}`,
        patches,
      })
      setPlan(updated)
      setToastMsg({ text: `Room updated (v${updated.current_version})`, type: 'success' })
    } catch (err: any) {
      setToastMsg({ text: err?.message || 'Failed to update room properties', type: 'error' })
    } finally {
      setPatching(false)
    }
  }

  // Apply Opening Properties Edit
  const handleSaveOpeningProperties = async () => {
    if (!plan || !selectedElement || selectedElement.type !== 'opening') return
    const width = parseFloat(propOpeningWidth)
    const offset = parseFloat(propOpeningOffset)
    const patches: any[] = []

    if (!isNaN(width) && width > 0) {
      patches.push({
        type: 'resize_opening',
        opening_id: selectedElement.id,
        width_mm: width,
      })
    }
    if (!isNaN(offset) && offset >= 0) {
      patches.push({
        type: 'move_opening',
        opening_id: selectedElement.id,
        offset_mm: offset,
      })
    }
    if (!patches.length) return

    try {
      setPatching(true)
      const updated = await api.applyPatches(plan.id, {
        message: `Modified opening ${selectedElement.id}`,
        patches,
      })
      setPlan(updated)
      setToastMsg({ text: `Opening updated (v${updated.current_version})`, type: 'success' })
    } catch (err: any) {
      setToastMsg({ text: err?.message || 'Failed to update opening', type: 'error' })
    } finally {
      setPatching(false)
    }
  }

  // Delete Opening
  const handleDeleteOpening = async () => {
    if (!plan || !selectedElement || selectedElement.type !== 'opening') return
    try {
      setPatching(true)
      const updated = await api.applyPatches(plan.id, {
        message: `Removed opening ${selectedElement.id}`,
        patches: [
          {
            type: 'remove_opening',
            opening_id: selectedElement.id,
          },
        ],
      })
      setPlan(updated)
      setSelectedElement(null)
      setToastMsg({ text: `Opening deleted (v${updated.current_version})`, type: 'success' })
    } catch (err: any) {
      setToastMsg({ text: err?.message || 'Failed to remove opening', type: 'error' })
    } finally {
      setPatching(false)
    }
  }

  // Mouse / Canvas Coordinate Conversion
  const screenToPlanMm = (clientX: number, clientY: number): { x: number; y: number } => {
    if (!svgRef.current) return { x: 0, y: 0 }
    const rect = svgRef.current.getBoundingClientRect()
    const s = 0.04 * zoom
    const svgX = clientX - rect.left - pan.x
    const svgY = clientY - rect.top - pan.y
    return {
      x: Math.round(svgX / s),
      y: Math.round(svgY / s),
    }
  }

  // Wall Drag Handlers (50mm grid snapping)
  const handleWallMouseDown = (e: React.MouseEvent, wallId: string) => {
    e.stopPropagation()
    const pt = screenToPlanMm(e.clientX, e.clientY)
    setDraggingWallId(wallId)
    setDragStartPos(pt)
    setDragCurrentDelta({ dx: 0, dy: 0 })
    setSelectedElement({ type: 'wall', id: wallId })
  }

  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    const pt = screenToPlanMm(e.clientX, e.clientY)
    setCursorMm(pt)

    if (isPanning) {
      setPan({
        x: pan.x + (e.clientX - panStart.x),
        y: pan.y + (e.clientY - panStart.y),
      })
      setPanStart({ x: e.clientX, y: e.clientY })
    } else if (draggingWallId && dragStartPos) {
      const rawDx = pt.x - dragStartPos.x
      const rawDy = pt.y - dragStartPos.y
      // 50mm grid snap
      const snapDx = Math.round(rawDx / 50) * 50
      const snapDy = Math.round(rawDy / 50) * 50
      setDragCurrentDelta({ dx: snapDx, dy: snapDy })
    }
  }

  const handleCanvasMouseUp = async () => {
    if (isPanning) {
      setIsPanning(false)
    }
    if (draggingWallId && plan && (dragCurrentDelta.dx !== 0 || dragCurrentDelta.dy !== 0)) {
      const wallId = draggingWallId
      const dx = dragCurrentDelta.dx
      const dy = dragCurrentDelta.dy
      setDraggingWallId(null)
      setDragStartPos(null)
      setDragCurrentDelta({ dx: 0, dy: 0 })

      try {
        setPatching(true)
        const updated = await api.applyPatches(plan.id, {
          message: `Moved wall ${wallId} by (${dx}mm, ${dy}mm)`,
          patches: [
            {
              type: 'move_wall',
              wall_id: wallId,
              dx_mm: dx,
              dy_mm: dy,
            },
          ],
        })
        setPlan(updated)
        setToastMsg({ text: `Wall moved: dx=${dx}mm, dy=${dy}mm (v${updated.current_version})`, type: 'success' })
      } catch (err: any) {
        setToastMsg({ text: err?.message || 'Move wall failed topological validation', type: 'error' })
      } finally {
        setPatching(false)
      }
    } else {
      setDraggingWallId(null)
      setDragStartPos(null)
      setDragCurrentDelta({ dx: 0, dy: 0 })
    }
  }

  // Click on Review Issue to Zoom & Highlight
  const handleIssueClick = (issue: Issue) => {
    setHighlightedElementIds(issue.element_ids)
    if (!activeLevel) return

    const firstId = issue.element_ids[0]
    const matchedRoom = activeLevel.rooms.find((r) => r.id === firstId)
    const matchedWall = activeLevel.walls.find((w) => w.id === firstId)

    if (matchedRoom) {
      const xs = matchedRoom.polygon.map((p) => p[0])
      const ys = matchedRoom.polygon.map((p) => p[1])
      const cx = (Math.min(...xs) + Math.max(...xs)) / 2
      const cy = (Math.min(...ys) + Math.max(...ys)) / 2
      setSelectedElement({ type: 'room', id: matchedRoom.id })
      setPan({ x: 260 - cx * 0.04 * zoom, y: 220 - cy * 0.04 * zoom })
    } else if (matchedWall) {
      const cx = (matchedWall.start[0] + matchedWall.end[0]) / 2
      const cy = (matchedWall.start[1] + matchedWall.end[1]) / 2
      setSelectedElement({ type: 'wall', id: matchedWall.id })
      setPan({ x: 260 - cx * 0.04 * zoom, y: 220 - cy * 0.04 * zoom })
    }
  }

  // Compute overall bounding box of level for dimensions
  const planBounds = useMemo(() => {
    if (!activeLevel || !activeLevel.walls.length) {
      return { minX: 0, minY: 0, maxX: 12000, maxY: 10000, width: 12000, height: 10000 }
    }
    const allX: number[] = []
    const allY: number[] = []
    activeLevel.walls.forEach((w) => {
      allX.push(w.start[0], w.end[0])
      allY.push(w.start[1], w.end[1])
    })
    const minX = Math.min(...allX)
    const maxX = Math.max(...allX)
    const minY = Math.min(...allY)
    const maxY = Math.max(...allY)
    return { minX, minY, maxX, maxY, width: maxX - minX, height: maxY - minY }
  }, [activeLevel])

  const scale = 0.04

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-2 border-[var(--ink-24)] border-t-[var(--accent)] rounded-full animate-spin" />
          <span className="font-mono text-[12px] text-[var(--ink-48)] uppercase tracking-wider">
            Loading Architectural Plan Workspace...
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 text-left">
      {/* Top Action Bar & Workspace Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-[var(--paper-wash)] border border-[var(--line)]">
        <div className="flex items-center gap-3">
          <BracketLabel text={`v${plan?.current_version || 1}`} />
          <span className="font-sans font-semibold text-[15px] text-[var(--ink)]">
            {plan?.name || 'Architectural Floor Plan'}
          </span>
          <span className="font-mono text-[11px] text-[var(--ink-48)] uppercase tracking-wider">
            Units: {plan?.data.units || 'MM'} · Snap: 50MM
          </span>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Level Switcher */}
          {plan && plan.data.levels.length > 1 && (
            <div className="flex items-center bg-[var(--paper)] border border-[var(--line)] p-0.5">
              {plan.data.levels.map((lvl, idx) => (
                <button
                  key={lvl.id}
                  type="button"
                  onClick={() => setCurrentLevelIdx(idx)}
                  className={`px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider transition-colors ${
                    currentLevelIdx === idx
                      ? 'bg-[var(--ink)] text-[var(--paper)] font-bold'
                      : 'text-[var(--ink-72)] hover:text-[var(--ink)]'
                  }`}
                >
                  {lvl.name}
                </button>
              ))}
            </div>
          )}

          {/* Dimension Toggle */}
          <Button
            label={showDimensions ? 'Hide Dims' : 'Show Dims'}
            variant={showDimensions ? 'accent' : 'ghost'}
            size="sm"
            icon={null}
            onClick={() => setShowDimensions(!showDimensions)}
          />

          {/* Undo / Redo */}
          <Button
            label="Undo"
            variant="ghost"
            size="sm"
            icon={null}
            disabled={!plan || plan.current_version <= 1}
            onClick={handleUndo}
            title="Undo (Ctrl+Z)"
          />
          <Button
            label="Redo"
            variant="ghost"
            size="sm"
            icon={null}
            disabled={!plan}
            onClick={handleRedo}
            title="Redo (Ctrl+Shift+Z)"
          />

          {/* Statutory Review Button */}
          <Button
            label={reviewing ? 'Checking...' : 'Run Review →'}
            variant="accent"
            size="sm"
            icon={null}
            disabled={reviewing}
            onClick={handleRunReview}
          />

          {/* Versions History */}
          <Button
            label={`Versions (${plan?.current_version || 1})`}
            variant="ghost"
            size="sm"
            icon={null}
            onClick={handleOpenHistory}
          />

          {/* Quick Fixture Scheme Loader */}
          <div className="relative inline-block">
            <select
              aria-label="Load Prebuilt Architectural Scheme"
              onChange={(e) => {
                const opt = FIXTURE_OPTIONS.find((f) => f.id === e.target.value)
                if (opt) handleImportFixture(opt.data, opt.name)
              }}
              className="h-8 px-2 font-mono text-[11px] uppercase tracking-wider bg-[var(--paper)] text-[var(--ink)] border border-[var(--line)] outline-none"
              defaultValue=""
            >
              <option value="" disabled>Load Fixture...</option>
              {FIXTURE_OPTIONS.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Main Split Grid: 8 Cols Drafting Canvas | 4 Cols Review & Properties */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: 2D Interactive SVG Drafting Workspace (8 Cols) */}
        <div className="lg:col-span-8 flex flex-col gap-3">
          <div className="relative border border-[var(--line)] bg-[var(--paper)] overflow-hidden shadow-sm">
            {/* Canvas Header & Pan/Zoom Readouts */}
            <div className="absolute top-2 left-2 z-10 flex items-center gap-2 bg-[var(--paper)]/90 backdrop-blur-sm px-2 py-1 border border-[var(--line)]">
              <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--ink-48)]">
                Zoom: {(zoom * 100).toFixed(0)}%
              </span>
              <button
                type="button"
                onClick={() => setZoom((z) => Math.min(z + 0.2, 3.0))}
                className="w-5 h-5 flex items-center justify-center font-mono font-bold text-[12px] border border-[var(--line)] hover:bg-[var(--line)]"
                title="Zoom In"
              >
                +
              </button>
              <button
                type="button"
                onClick={() => setZoom((z) => Math.max(z - 0.2, 0.4))}
                className="w-5 h-5 flex items-center justify-center font-mono font-bold text-[12px] border border-[var(--line)] hover:bg-[var(--line)]"
                title="Zoom Out"
              >
                -
              </button>
              <button
                type="button"
                onClick={() => {
                  setZoom(1.0)
                  setPan({ x: 100, y: 70 })
                }}
                className="px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider border border-[var(--line)] hover:bg-[var(--line)]"
                title="Reset View"
              >
                Reset
              </button>
            </div>

            {/* Live Cursor Coordinate Readout */}
            <div className="absolute bottom-2 right-2 z-10 bg-[var(--paper)]/90 backdrop-blur-sm px-2 py-1 border border-[var(--line)]">
              {cursorMm ? (
                <div className="flex items-center gap-2">
                  <CoordLabel axis="X" value={cursorMm.x} unit="MM" />
                  <CoordLabel axis="Y" value={cursorMm.y} unit="MM" />
                </div>
              ) : (
                <span className="font-mono text-[11px] text-[var(--ink-48)]">Cursor Outside</span>
              )}
            </div>

            {/* SVG Canvas with Grid Background */}
            <svg
              ref={svgRef}
              className="w-full h-[580px] cursor-crosshair select-none bg-[var(--paper)]"
              onMouseDown={(e) => {
                if (e.target === svgRef.current || (e.target as HTMLElement).tagName === 'rect') {
                  setIsPanning(true)
                  setPanStart({ x: e.clientX, y: e.clientY })
                  setSelectedElement(null)
                }
              }}
              onMouseMove={handleCanvasMouseMove}
              onMouseUp={handleCanvasMouseUp}
              onMouseLeave={() => {
                setCursorMm(null)
                setIsPanning(false)
                setDraggingWallId(null)
              }}
            >
              <defs>
                {/* 500mm Drafting Grid Pattern */}
                <pattern
                  id="drafting-subgrid"
                  width={500 * scale * zoom}
                  height={500 * scale * zoom}
                  patternUnits="userSpaceOnUse"
                >
                  <path
                    d={`M ${500 * scale * zoom} 0 L 0 0 0 ${500 * scale * zoom}`}
                    fill="none"
                    stroke="rgba(40, 40, 40, 0.05)"
                    strokeWidth="0.5"
                  />
                </pattern>
                {/* 2000mm Major Grid */}
                <pattern
                  id="drafting-major-grid"
                  width={2000 * scale * zoom}
                  height={2000 * scale * zoom}
                  patternUnits="userSpaceOnUse"
                >
                  <rect
                    width={2000 * scale * zoom}
                    height={2000 * scale * zoom}
                    fill="url(#drafting-subgrid)"
                  />
                  <path
                    d={`M ${2000 * scale * zoom} 0 L 0 0 0 ${2000 * scale * zoom}`}
                    fill="none"
                    stroke="rgba(40, 40, 40, 0.12)"
                    strokeWidth="1"
                  />
                </pattern>
              </defs>

              {/* Grid Background */}
              <rect width="100%" height="100%" fill="url(#drafting-major-grid)" />

              {/* Scaled & Panned Floor Plan Hierarchy */}
              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* 1. Legal Envelope Overlay (if available) */}
                {envelope && envelope.footprint_polygon && (
                  <polygon
                    points={envelope.footprint_polygon
                      .map((p) => `${p[0] * scale},${p[1] * scale}`)
                      .join(' ')}
                    fill="rgba(60, 138, 82, 0.03)"
                    stroke="#3c8a52"
                    strokeWidth="1.5"
                    strokeDasharray="4 4"
                  />
                )}

                {/* 2. Rooms Polygon Fills & Area Labels */}
                {activeLevel?.rooms.map((room) => {
                  const isSelected = selectedElement?.id === room.id
                  const isHighlighted = highlightedElementIds.includes(room.id)
                  const xs = room.polygon.map((p) => p[0] * scale)
                  const ys = room.polygon.map((p) => p[1] * scale)
                  const cx = (Math.min(...xs) + Math.max(...xs)) / 2
                  const cy = (Math.min(...ys) + Math.max(...ys)) / 2
                  const pointsStr = room.polygon
                    .map((p) => `${p[0] * scale},${p[1] * scale}`)
                    .join(' ')

                  let areaMm2 = 0
                  for (let i = 0; i < room.polygon.length; i++) {
                    const j = (i + 1) % room.polygon.length
                    areaMm2 += room.polygon[i][0] * room.polygon[j][1]
                    areaMm2 -= room.polygon[j][0] * room.polygon[i][1]
                  }
                  const areaSqm = Math.abs(areaMm2) / 2_000_000

                  return (
                    <g
                      key={room.id}
                      onClick={(e) => {
                        e.stopPropagation()
                        setSelectedElement({ type: 'room', id: room.id })
                      }}
                    >
                      <polygon
                        points={pointsStr}
                        fill={
                          isHighlighted
                            ? 'rgba(250, 54, 0, 0.12)'
                            : isSelected
                            ? 'rgba(40, 40, 40, 0.10)'
                            : 'rgba(40, 40, 40, 0.04)'
                        }
                        stroke={isHighlighted ? '#fa3600' : isSelected ? '#282828' : 'rgba(40, 40, 40, 0.2)'}
                        strokeWidth={isHighlighted || isSelected ? 2 : 1}
                        className="transition-colors cursor-pointer"
                      />
                      <text
                        x={cx}
                        y={cy - 6}
                        textAnchor="middle"
                        fontFamily="var(--f-sans, sans-serif)"
                        fontSize="11"
                        fontWeight="600"
                        fill="var(--ink)"
                        className="pointer-events-none select-none"
                      >
                        {room.name}
                      </text>
                      <text
                        x={cx}
                        y={cy + 8}
                        textAnchor="middle"
                        fontFamily="var(--f-mono, monospace)"
                        fontSize="9"
                        fill="var(--ink-72)"
                        className="pointer-events-none select-none"
                      >
                        {areaSqm.toFixed(2)} m²
                      </text>
                    </g>
                  )
                })}

                {/* 3. Stairs Flights */}
                {activeLevel?.stairs.map((stair) => {
                  const isHighlighted = highlightedElementIds.includes(stair.id)
                  const isSelected = selectedElement?.id === stair.id
                  const ptsStr = stair.polygon
                    .map((p) => `${p[0] * scale},${p[1] * scale}`)
                    .join(' ')
                  const xs = stair.polygon.map((p) => p[0] * scale)
                  const ys = stair.polygon.map((p) => p[1] * scale)
                  const cx = (Math.min(...xs) + Math.max(...xs)) / 2
                  const cy = (Math.min(...ys) + Math.max(...ys)) / 2

                  return (
                    <g
                      key={stair.id}
                      onClick={(e) => {
                        e.stopPropagation()
                        setSelectedElement({ type: 'stair', id: stair.id })
                      }}
                    >
                      <polygon
                        points={ptsStr}
                        fill={isHighlighted ? 'rgba(250, 54, 0, 0.15)' : 'rgba(200, 195, 180, 0.25)'}
                        stroke={isHighlighted ? '#fa3600' : isSelected ? '#282828' : '#888'}
                        strokeWidth={1.5}
                        className="cursor-pointer"
                      />
                      <line
                        x1={Math.min(...xs)}
                        y1={cy}
                        x2={Math.max(...xs)}
                        y2={cy}
                        stroke="#666"
                        strokeWidth="1"
                        strokeDasharray="3 3"
                      />
                      <text
                        x={cx}
                        y={cy - 2}
                        textAnchor="middle"
                        fontFamily="var(--f-mono, monospace)"
                        fontSize="9"
                        fontWeight="bold"
                        fill="var(--ink-72)"
                        className="pointer-events-none select-none"
                      >
                        STAIR ({stair.direction.toUpperCase()})
                      </text>
                    </g>
                  )
                })}

                {/* 4. Walls with Structural Thickness & Dragging */}
                {activeLevel?.walls.map((wall) => {
                  const isDragging = draggingWallId === wall.id
                  const isSelected = selectedElement?.id === wall.id
                  const isHighlighted = highlightedElementIds.includes(wall.id)

                  const dx = isDragging ? dragCurrentDelta.dx : 0
                  const dy = isDragging ? dragCurrentDelta.dy : 0
                  const x1 = (wall.start[0] + dx) * scale
                  const y1 = (wall.start[1] + dy) * scale
                  const x2 = (wall.end[0] + dx) * scale
                  const y2 = (wall.end[1] + dy) * scale
                  const strokeWidthPx = Math.max(wall.thickness_mm * scale, 3)

                  return (
                    <g
                      key={wall.id}
                      onMouseDown={(e) => handleWallMouseDown(e, wall.id)}
                      className="cursor-move"
                    >
                      <line
                        x1={x1}
                        y1={y1}
                        x2={x2}
                        y2={y2}
                        stroke={
                          isHighlighted
                            ? '#fa3600'
                            : isSelected
                            ? '#282828'
                            : wall.is_external
                            ? '#1a1a1a'
                            : '#3a3a3a'
                        }
                        strokeWidth={strokeWidthPx}
                        strokeLinecap="round"
                        className="transition-colors"
                      />
                      {(isSelected || isHighlighted) && (
                        <line
                          x1={x1}
                          y1={y1}
                          x2={x2}
                          y2={y2}
                          stroke={isHighlighted ? '#fa3600' : '#4f46e5'}
                          strokeWidth={strokeWidthPx + 3}
                          strokeOpacity={0.4}
                          strokeLinecap="round"
                          fill="none"
                        />
                      )}
                    </g>
                  )
                })}

                {/* 5. Openings: Doors (Swing Arcs) and Windows (Glazing) */}
                {activeLevel?.openings.map((op) => {
                  const hostWall = activeLevel.walls.find((w) => w.id === op.wall_id)
                  if (!hostWall) return null

                  const isSelected = selectedElement?.id === op.id
                  const isHighlighted = highlightedElementIds.includes(op.id)

                  const wdx = hostWall.end[0] - hostWall.start[0]
                  const wdy = hostWall.end[1] - hostWall.start[1]
                  const len = Math.hypot(wdx, wdy)
                  if (len === 0) return null

                  const ux = wdx / len
                  const uy = wdy / len
                  const nx = -uy
                  const ny = ux

                  const startX = (hostWall.start[0] + ux * op.offset_mm) * scale
                  const startY = (hostWall.start[1] + uy * op.offset_mm) * scale
                  const endX = (hostWall.start[0] + ux * (op.offset_mm + op.width_mm)) * scale
                  const endY = (hostWall.start[1] + uy * (op.offset_mm + op.width_mm)) * scale
                  const widthPx = op.width_mm * scale

                  if (op.kind === 'door') {
                    const leafEndX = startX + nx * widthPx
                    const leafEndY = startY + ny * widthPx

                    return (
                      <g
                        key={op.id}
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedElement({ type: 'opening', id: op.id })
                        }}
                        className="cursor-pointer"
                      >
                        <line
                          x1={startX}
                          y1={startY}
                          x2={endX}
                          y2={endY}
                          stroke="var(--paper)"
                          strokeWidth={hostWall.thickness_mm * scale + 1}
                        />
                        <line
                          x1={startX}
                          y1={startY}
                          x2={leafEndX}
                          y2={leafEndY}
                          stroke={isHighlighted ? '#fa3600' : isSelected ? '#4f46e5' : '#282828'}
                          strokeWidth="2"
                        />
                        <path
                          d={`M ${endX} ${endY} A ${widthPx} ${widthPx} 0 0 0 ${leafEndX} ${leafEndY}`}
                          fill="none"
                          stroke={isHighlighted ? '#fa3600' : 'rgba(40, 40, 40, 0.4)'}
                          strokeWidth="1"
                          strokeDasharray="2 2"
                        />
                      </g>
                    )
                  } else {
                    return (
                      <g
                        key={op.id}
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedElement({ type: 'opening', id: op.id })
                        }}
                        className="cursor-pointer"
                      >
                        <line
                          x1={startX}
                          y1={startY}
                          x2={endX}
                          y2={endY}
                          stroke="var(--paper)"
                          strokeWidth={hostWall.thickness_mm * scale}
                        />
                        <line
                          x1={startX + nx * 2}
                          y1={startY + ny * 2}
                          x2={endX + nx * 2}
                          y2={endY + ny * 2}
                          stroke={isHighlighted ? '#fa3600' : isSelected ? '#4f46e5' : '#2563eb'}
                          strokeWidth="1.5"
                        />
                        <line
                          x1={startX - nx * 2}
                          y1={startY - ny * 2}
                          x2={endX - nx * 2}
                          y2={endY - ny * 2}
                          stroke={isHighlighted ? '#fa3600' : isSelected ? '#4f46e5' : '#2563eb'}
                          strokeWidth="1.5"
                        />
                      </g>
                    )
                  }
                })}

                {/* 6. Dimension Annotation Lines (Toggleable) */}
                {showDimensions && (
                  <g className="pointer-events-none select-none font-mono text-[9px] fill-[var(--ink-72)]">
                    <line
                      x1={planBounds.minX * scale}
                      y1={(planBounds.minY - 800) * scale}
                      x2={planBounds.maxX * scale}
                      y2={(planBounds.minY - 800) * scale}
                      stroke="var(--ink-48)"
                      strokeWidth="1"
                    />
                    <text
                      x={((planBounds.minX + planBounds.maxX) / 2) * scale}
                      y={(planBounds.minY - 950) * scale}
                      textAnchor="middle"
                    >
                      {Math.round(planBounds.width)} MM
                    </text>

                    <line
                      x1={(planBounds.minX - 800) * scale}
                      y1={planBounds.minY * scale}
                      x2={(planBounds.minX - 800) * scale}
                      y2={planBounds.maxY * scale}
                      stroke="var(--ink-48)"
                      strokeWidth="1"
                    />
                    <text
                      x={(planBounds.minX - 950) * scale}
                      y={((planBounds.minY + planBounds.maxY) / 2) * scale}
                      textAnchor="middle"
                      transform={`rotate(-90 ${(planBounds.minX - 950) * scale} ${
                        ((planBounds.minY + planBounds.maxY) / 2) * scale
                      })`}
                    >
                      {Math.round(planBounds.height)} MM
                    </text>
                  </g>
                )}
              </g>
            </svg>
          </div>
        </div>

        {/* Right Column: Statutory Review Console & Properties Inspector (4 Cols) */}
        <div className="lg:col-span-4 flex flex-col gap-4">
          {/* Properties Inspector Panel */}
          {selectedElement && (
            <Card
              title={`Element Inspector: ${selectedElement.type.toUpperCase()}`}
              subtitle={`ID: ${selectedElement.id}`}
              darkHeader
            >
              <div className="flex flex-col gap-3 text-left">
                {selectedElement.type === 'wall' && (
                  <>
                    <Input
                      label="Wall Thickness (mm)"
                      type="number"
                      value={propWallThickness}
                      onChange={(e) => setPropWallThickness(e.target.value)}
                    />
                    <Button
                      label={patching ? 'Saving...' : 'Apply Wall Patch'}
                      variant="accent"
                      size="sm"
                      icon={null}
                      disabled={patching}
                      onClick={handleSaveWallThickness}
                    />
                  </>
                )}

                {selectedElement.type === 'room' && (
                  <>
                    <Input
                      label="Room Display Name"
                      type="text"
                      value={propRoomName}
                      onChange={(e) => setPropRoomName(e.target.value)}
                    />
                    <div className="flex flex-col gap-1">
                      <label className="font-mono text-[11px] uppercase tracking-wider text-[var(--ink-72)]">
                        Room Function Type
                      </label>
                      <select
                        value={propRoomType}
                        onChange={(e) => setPropRoomType(e.target.value)}
                        className="h-9 px-2 font-mono text-[12px] bg-[var(--paper)] text-[var(--ink)] border border-[var(--line)]"
                      >
                        <option value="living">Living & Dining</option>
                        <option value="bedroom">Habitable Bedroom</option>
                        <option value="kitchen">Kitchen</option>
                        <option value="bathroom">Bathroom</option>
                        <option value="wc">Water Closet (WC)</option>
                        <option value="corridor">Passage / Corridor</option>
                        <option value="study">Study</option>
                      </select>
                    </div>
                    <Button
                      label={patching ? 'Saving...' : 'Apply Room Patch'}
                      variant="accent"
                      size="sm"
                      icon={null}
                      disabled={patching}
                      onClick={handleSaveRoomProperties}
                    />
                  </>
                )}

                {selectedElement.type === 'opening' && (
                  <>
                    <Input
                      label="Clear Width (mm)"
                      type="number"
                      value={propOpeningWidth}
                      onChange={(e) => setPropOpeningWidth(e.target.value)}
                    />
                    <Input
                      label="Wall Offset (mm)"
                      type="number"
                      value={propOpeningOffset}
                      onChange={(e) => setPropOpeningOffset(e.target.value)}
                    />
                    <div className="flex items-center gap-2 pt-1">
                      <Button
                        label={patching ? 'Saving...' : 'Save Opening'}
                        variant="accent"
                        size="sm"
                        icon={null}
                        disabled={patching}
                        onClick={handleSaveOpeningProperties}
                      />
                      <Button
                        label="Remove"
                        variant="ghost"
                        size="sm"
                        icon={null}
                        onClick={handleDeleteOpening}
                      />
                    </div>
                  </>
                )}
              </div>
            </Card>
          )}

          {/* Statutory Review Console Card (Landing Page Review Style) */}
          <Card
            title="Review · Statutory Code Compliance"
            subtitle={`Ruleset: ${rulesetId || 'National Building Code 2016'}`}
            darkHeader
          >
            {reviewResult ? (
              <div className="flex flex-col gap-3 text-left">
                {/* Metric Summary Header Pills */}
                <div className="flex items-center justify-between pb-2 border-b border-[var(--line)]">
                  <span className="font-mono text-[12px] font-bold text-[var(--ink)]">
                    {reviewResult.summary.fail_count === 0
                      ? 'Fully Code Compliant'
                      : `${reviewResult.summary.fail_count} open violation(s)`}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <StatusPill status="fail" label={`${reviewResult.summary.fail_count} Fail`} />
                    <StatusPill status="review" label={`${reviewResult.summary.review_count} Rev`} />
                    <StatusPill status="pass" label={`${reviewResult.summary.pass_count} Pass`} />
                  </div>
                </div>

                {/* Filter Tabs */}
                <div className="flex items-center gap-1 border-b border-[var(--line)] pb-1.5 font-mono text-[11px]">
                  {(['all', 'fail', 'review', 'pass'] as const).map((tab) => (
                    <button
                      key={tab}
                      type="button"
                      onClick={() => setReviewFilter(tab)}
                      className={`px-2 py-0.5 uppercase tracking-wider ${
                        reviewFilter === tab
                          ? 'bg-[var(--ink)] text-[var(--paper)] font-bold'
                          : 'text-[var(--ink-48)] hover:text-[var(--ink)]'
                      }`}
                    >
                      {tab}
                    </button>
                  ))}
                </div>

                {/* Issues List with Click-to-Highlight */}
                <div className="flex flex-col gap-2 max-h-[380px] overflow-y-auto pr-1">
                  {reviewResult.issues
                    .filter((item) => reviewFilter === 'all' || item.status === reviewFilter)
                    .map((issue) => (
                      <div
                        key={issue.id}
                        onClick={() => handleIssueClick(issue)}
                        className={`p-2.5 border transition-all cursor-pointer ${
                          highlightedElementIds.some((id) => issue.element_ids.includes(id))
                            ? 'border-[var(--accent)] bg-[var(--paper-wash)] shadow-sm'
                            : 'border-[var(--line)] hover:border-[var(--ink-48)]'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <BracketLabel text={issue.category} />
                          <StatusPill status={issue.status} />
                        </div>
                        <p className="font-sans text-[12px] font-medium text-[var(--ink)] mb-1">
                          {issue.message}
                        </p>
                        <div className="flex flex-col gap-0.5 font-mono text-[10px] text-[var(--ink-72)]">
                          <DataRow label="Measured" value={String(issue.measured)} />
                          <DataRow label="Required" value={String(issue.required)} />
                          <span className="text-[var(--ink-48)] pt-0.5">{issue.clause}</span>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center p-6 text-center gap-2">
                <span className="font-mono text-[12px] text-[var(--ink-48)]">
                  No review conducted on current scheme.
                </span>
                <Button
                  label="Run Statutory Review →"
                  variant="accent"
                  size="sm"
                  icon={null}
                  onClick={handleRunReview}
                />
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Version History Drawer Modal */}
      {showVersionsDrawer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-xl bg-[var(--paper)] border border-[var(--line)] shadow-xl p-5 flex flex-col gap-4 text-left">
            <div className="flex items-center justify-between border-b border-[var(--line)] pb-3">
              <div>
                <h3 className="font-sans font-bold text-[16px] text-[var(--ink)]">
                  Version History Log
                </h3>
                <span className="font-mono text-[11px] text-[var(--ink-48)] uppercase tracking-wider">
                  Plan ID: {plan?.id} · Current: v{plan?.current_version}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setShowVersionsDrawer(false)}
                className="w-7 h-7 flex items-center justify-center font-mono text-[14px] border border-[var(--line)] hover:bg-[var(--line)]"
              >
                ✕
              </button>
            </div>

            <div className="flex flex-col gap-2 max-h-[400px] overflow-y-auto">
              {versions.map((v) => (
                <div
                  key={v.id}
                  className={`p-3 border flex items-center justify-between ${
                    v.version === plan?.current_version
                      ? 'border-[var(--ink)] bg-[var(--paper-wash)]'
                      : 'border-[var(--line)]'
                  }`}
                >
                  <div className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-[12px] text-[var(--ink)]">
                        VERSION [{v.version.toString().padStart(2, '0')}]
                      </span>
                      <span className="px-1.5 py-0.2 bg-[var(--line)] font-mono text-[9px] uppercase tracking-wider text-[var(--ink-72)]">
                        {v.created_by}
                      </span>
                    </div>
                    <span className="font-sans text-[12px] text-[var(--ink-72)]">
                      {v.message || 'Structural modification'}
                    </span>
                    <span className="font-mono text-[10px] text-[var(--ink-48)]">
                      {new Date(v.created_at).toLocaleString()}
                    </span>
                  </div>

                  {v.version !== plan?.current_version && (
                    <Button
                      label="View"
                      variant="ghost"
                      size="sm"
                      icon={null}
                      onClick={async () => {
                        try {
                          const historic = await api.getPlan(plan!.id, v.version)
                          setPlan(historic)
                          setShowVersionsDrawer(false)
                          setToastMsg({ text: `Viewing version ${v.version}`, type: 'success' })
                        } catch (err: any) {
                          setToastMsg({ text: err?.message || 'Failed to load version', type: 'error' })
                        }
                      }}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Toast Feedback */}
      {toastMsg && (
        <Toast
          message={toastMsg.text}
          type={toastMsg.type}
          onClose={() => setToastMsg(null)}
        />
      )}
    </div>
  )
}
