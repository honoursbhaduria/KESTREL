import React, { useEffect, useRef, useState, useCallback } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { api, type Issue } from '~/api/client'

interface PlanViewer3DProps {
  planId: string
  version: number
  northAngleDeg?: number
  selectedElementId?: string | null
  onSelectElement?: (element: { type: 'wall' | 'room' | 'stair'; id: string } | null) => void
  issues?: Issue[]
}

export const PlanViewer3D: React.FC<PlanViewer3DProps> = ({
  planId,
  version,
  northAngleDeg = 0,
  selectedElementId,
  onSelectElement,
  issues = [],
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  // Controls state
  const [navMode, setNavMode] = useState<'orbit' | 'walk'>('orbit')
  const [timeOfDay, setTimeOfDay] = useState<number>(12) // 9 = morning, 12 = noon, 17 = evening
  const [isolatedLevel, setIsolatedLevel] = useState<string>('all')
  const [availableLevels, setAvailableLevels] = useState<string[]>([])
  const [sectionHeight, setSectionHeight] = useState<number>(15) // meters cut-away

  // Scene references
  const sceneRef = useRef<THREE.Scene | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const modelRootRef = useRef<THREE.Group | null>(null)
  const sunLightRef = useRef<THREE.DirectionalLight | null>(null)
  const clipPlaneRef = useRef<THREE.Plane>(new THREE.Plane(new THREE.Vector3(0, -1, 0), 15))

  // Walkthrough navigation keys
  const keysPressed = useRef<{ [key: string]: boolean }>({})

  // Update Sun Direction and Color based on North Angle + Time of Day
  const updateSun = useCallback(() => {
    if (!sunLightRef.current) return
    const sun = sunLightRef.current

    // Elevation angle based on time (6h to 18h)
    const hour = Math.max(6, Math.min(18, timeOfDay))
    const sunElevation = Math.sin(((hour - 6) / 12) * Math.PI)
    const sunAzimuthRad = (northAngleDeg + (hour - 12) * 15) * (Math.PI / 180)

    const distance = 40
    sun.position.set(
      Math.sin(sunAzimuthRad) * distance,
      Math.max(5, sunElevation * distance),
      Math.cos(sunAzimuthRad) * distance
    )

    // Warmer tone for morning/evening, bright white for noon
    if (hour < 10 || hour > 15) {
      sun.color.setHex(0xffecd2)
      sun.intensity = 1.3
    } else {
      sun.color.setHex(0xffffff)
      sun.intensity = 1.6
    }
  }, [timeOfDay, northAngleDeg])

  useEffect(() => {
    updateSun()
  }, [updateSun])

  // Update clipping plane height
  useEffect(() => {
    clipPlaneRef.current.constant = sectionHeight
  }, [sectionHeight])

  // Update Level Isolation
  useEffect(() => {
    if (!modelRootRef.current) return
    modelRootRef.current.traverse((child) => {
      if (child instanceof THREE.Mesh || child instanceof THREE.Group) {
        // Find which level this node belongs to
        let curr: THREE.Object3D | null = child
        let levelName = ''
        while (curr && curr !== modelRootRef.current) {
          if (curr.name && (curr.name.toLowerCase().includes('level') || curr.name.toLowerCase().includes('floor'))) {
            levelName = curr.name
            break
          }
          curr = curr.parent
        }

        if (levelName) {
          if (isolatedLevel === 'all' || levelName === isolatedLevel) {
            child.visible = true
          } else {
            child.visible = false
          }
        }
      }
    })
  }, [isolatedLevel])

  // Update Selection and Violation Highlights in 3D
  useEffect(() => {
    if (!modelRootRef.current) return

    modelRootRef.current.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        const meshName = child.name || ''
        const isSelected = selectedElementId && meshName.includes(selectedElementId)
        const hasIssue = issues.some((i) => i.status === 'fail' && meshName.includes(i.id))

        if (Array.isArray(child.material)) return
        const mat = child.material as THREE.MeshStandardMaterial

        if (isSelected) {
          mat.emissive = new THREE.Color(0x3b82f6) // Blue selection glow
          mat.emissiveIntensity = 0.6
        } else if (hasIssue) {
          mat.emissive = new THREE.Color(0xef4444) // Red violation warning
          mat.emissiveIntensity = 0.5
        } else {
          mat.emissive = new THREE.Color(0x000000)
          mat.emissiveIntensity = 0.0
        }
      }
    })
  }, [selectedElementId, issues])

  // Main Scene Setup & Loader
  useEffect(() => {
    const container = mountRef.current
    if (!container) return

    const width = container.clientWidth || 800
    const height = container.clientHeight || 500

    // 1. Scene & Renderer
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0c0d0e)
    sceneRef.current = scene

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.localClippingEnabled = true
    container.innerHTML = ''
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
    camera.position.set(16, 14, 18)
    cameraRef.current = camera

    // 3. Orbit Controls
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.maxPolarAngle = Math.PI / 2 + 0.05 // Don't flip below ground
    controlsRef.current = controls

    // 4. Lighting
    const ambient = new THREE.AmbientLight(0xffffff, 0.6)
    scene.add(ambient)

    const sun = new THREE.DirectionalLight(0xffffff, 1.5)
    sun.castShadow = true
    sun.shadow.mapSize.width = 1024
    sun.shadow.mapSize.height = 1024
    scene.add(sun)
    sunLightRef.current = sun

    // Grid Floor
    const gridHelper = new THREE.GridHelper(50, 50, 0x333333, 0x1f1f1f)
    gridHelper.position.y = -0.01
    scene.add(gridHelper)

    // 5. Fetch and Parse GLB
    setLoading(true)
    setLoadError(null)

    let isSubscribed = true
    api.getPlanGlbBuffer(planId, version)
      .then((buffer) => {
        if (!isSubscribed) return

        const loader = new GLTFLoader()
        loader.parse(
          buffer,
          '',
          (gltf) => {
            if (!isSubscribed) return
            const root = gltf.scene
            modelRootRef.current = root

            // Enable clipping on all mesh materials
            const levelsFound: string[] = []
            root.traverse((child) => {
              if (child.name && (child.name.toLowerCase().includes('level') || child.name.toLowerCase().includes('floor'))) {
                if (!levelsFound.includes(child.name)) {
                  levelsFound.push(child.name)
                }
              }
              if (child instanceof THREE.Mesh) {
                child.castShadow = true
                child.receiveShadow = true
                if (child.material) {
                  const m = child.material as THREE.MeshStandardMaterial
                  m.clippingPlanes = [clipPlaneRef.current]
                  m.clipShadows = true
                }
              }
            })

            if (levelsFound.length > 0) {
              setAvailableLevels(levelsFound)
            }

            // Center and scale camera to frame model
            const bbox = new THREE.Box3().setFromObject(root)
            const center = bbox.getCenter(new THREE.Vector3())
            const size = bbox.getSize(new THREE.Vector3())

            root.position.sub(center) // Center around (0, 0, 0)
            root.position.y += size.y / 2 // Rest on ground
            scene.add(root)

            const maxDim = Math.max(size.x, size.y, size.z)
            camera.position.set(maxDim * 1.2, maxDim * 1.0, maxDim * 1.2)
            controls.target.set(0, size.y / 3, 0)
            controls.update()

            setLoading(false)
          },
          (err) => {
            if (!isSubscribed) return
            setLoadError('Failed to parse 3D GLB model')
            setLoading(false)
          }
        )
      })
      .catch((err) => {
        if (!isSubscribed) return
        setLoadError(err instanceof Error ? err.message : 'Error fetching 3D model')
        setLoading(false)
      })

    // 6. Click Raycasting for Shared Selection Sync
    const raycaster = new THREE.Raycaster()
    const mouse = new THREE.Vector2()

    const handleClick = (e: MouseEvent) => {
      if (!renderer.domElement || !modelRootRef.current) return
      const rect = renderer.domElement.getBoundingClientRect()
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

      raycaster.setFromCamera(mouse, camera)
      const intersects = raycaster.intersectObjects(modelRootRef.current.children, true)

      if (intersects.length > 0) {
        const hit = intersects[0].object
        const name = hit.name || ''
        let elemType: 'wall' | 'room' | 'stair' = 'wall'
        let elemId = ''

        if (name.startsWith('Wall_')) {
          elemType = 'wall'
          elemId = name.replace('Wall_', '')
        } else if (name.startsWith('Slab_')) {
          elemType = 'room'
          elemId = name.replace('Slab_', '')
        } else if (name.startsWith('StairStep_')) {
          elemType = 'stair'
          elemId = name.split('_')[1] || ''
        }

        if (elemId && onSelectElement) {
          onSelectElement({ type: elemType, id: elemId })
        }
      }
    }

    renderer.domElement.addEventListener('click', handleClick)

    // 7. Key Listeners for WASD Walkthrough
    const handleKeyDown = (e: KeyboardEvent) => {
      keysPressed.current[e.key.toLowerCase()] = true
    }
    const handleKeyUp = (e: KeyboardEvent) => {
      keysPressed.current[e.key.toLowerCase()] = false
    }
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)

    // 8. Animation & Render Loop
    let animId: number
    const clock = new THREE.Clock()

    const animate = () => {
      animId = requestAnimationFrame(animate)
      const delta = clock.getDelta()

      // Walkthrough mode movement
      if (navMode === 'walk') {
        const moveSpeed = 6 * delta
        const forward = new THREE.Vector3()
        camera.getWorldDirection(forward)
        forward.y = 0
        forward.normalize()

        const right = new THREE.Vector3()
        right.crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize()

        if (keysPressed.current['w'] || keysPressed.current['arrowup']) {
          camera.position.addScaledVector(forward, moveSpeed)
          controls.target.addScaledVector(forward, moveSpeed)
        }
        if (keysPressed.current['s'] || keysPressed.current['arrowdown']) {
          camera.position.addScaledVector(forward, -moveSpeed)
          controls.target.addScaledVector(forward, -moveSpeed)
        }
        if (keysPressed.current['a'] || keysPressed.current['arrowleft']) {
          camera.position.addScaledVector(right, -moveSpeed)
          controls.target.addScaledVector(right, -moveSpeed)
        }
        if (keysPressed.current['d'] || keysPressed.current['arrowright']) {
          camera.position.addScaledVector(right, moveSpeed)
          controls.target.addScaledVector(right, moveSpeed)
        }
      }

      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    // 9. Resize Observer
    const handleResize = () => {
      if (!container || !rendererRef.current || !cameraRef.current) return
      const w = container.clientWidth
      const h = container.clientHeight
      cameraRef.current.aspect = w / h
      cameraRef.current.updateProjectionMatrix()
      rendererRef.current.setSize(w, h)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      isSubscribed = false
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', handleResize)
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
      renderer.domElement.removeEventListener('click', handleClick)
      controls.dispose()
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [planId, version, navMode, onSelectElement])

  return (
    <div className="relative w-full h-full min-h-[500px] flex flex-col bg-[#0c0d0e] text-white select-none overflow-hidden rounded border border-[#222]">
      {/* 3D Canvas Mount Point */}
      <div ref={mountRef} className="w-full flex-1 min-h-[460px] cursor-grab active:cursor-grabbing" />

      {/* Loading Overlay */}
      {loading && (
        <div className="absolute inset-0 bg-[#0c0d0e]/80 backdrop-blur-sm flex flex-col items-center justify-center gap-3 z-20">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="mono text-xs text-gray-300">
            Generating glTF 2.0 Architectural Geometry...
          </span>
        </div>
      )}

      {/* Error Banner */}
      {loadError && (
        <div className="absolute top-4 left-4 right-4 bg-rose-950/90 border border-rose-700 p-3 rounded text-xs text-rose-200 z-30 mono flex items-center justify-between">
          <span>⚠️ {loadError}</span>
          <button
            onClick={() => window.location.reload()}
            className="underline hover:text-white"
          >
            Retry
          </button>
        </div>
      )}

      {/* 3D Floating Control Toolbar */}
      <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-2 bg-[#17181c]/90 backdrop-blur border border-[#333] p-1.5 rounded-md text-xs mono">
        {/* Navigation Mode */}
        <div className="flex rounded bg-[#24252b] p-0.5">
          <button
            onClick={() => setNavMode('orbit')}
            className={`px-2 py-1 rounded transition-colors ${
              navMode === 'orbit' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            Orbit
          </button>
          <button
            onClick={() => setNavMode('walk')}
            className={`px-2 py-1 rounded transition-colors ${
              navMode === 'walk' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
            title="Use WASD or arrow keys to walk"
          >
            Walk (WASD)
          </button>
        </div>

        {/* Level Isolation */}
        {availableLevels.length > 0 && (
          <select
            value={isolatedLevel}
            onChange={(e) => setIsolatedLevel(e.target.value)}
            className="bg-[#24252b] text-white border border-[#444] px-2 py-1 rounded text-xs focus:outline-none"
          >
            <option value="all">All Levels</option>
            {availableLevels.map((lvl) => (
              <option key={lvl} value={lvl}>
                {lvl}
              </option>
            ))}
          </select>
        )}

        {/* Sun Time of Day */}
        <div className="flex items-center gap-1.5 px-2 bg-[#24252b] rounded py-1">
          <span className="text-[10px] text-gray-400">Sun:</span>
          <input
            type="range"
            min="6"
            max="18"
            step="1"
            value={timeOfDay}
            onChange={(e) => setTimeOfDay(Number(e.target.value))}
            className="w-16 accent-amber-400 cursor-pointer"
          />
          <span className="text-[10px] text-amber-300 min-w-[28px]">{timeOfDay}:00</span>
        </div>

        {/* Section Height Slice */}
        <div className="flex items-center gap-1.5 px-2 bg-[#24252b] rounded py-1">
          <span className="text-[10px] text-gray-400">Cut-away:</span>
          <input
            type="range"
            min="1"
            max="20"
            step="0.5"
            value={sectionHeight}
            onChange={(e) => setSectionHeight(Number(e.target.value))}
            className="w-16 accent-indigo-400 cursor-pointer"
          />
          <span className="text-[10px] text-indigo-300 min-w-[24px]">{sectionHeight}m</span>
        </div>
      </div>

      {/* Bottom Status & Sync Badge */}
      <div className="absolute bottom-3 left-3 z-10 flex items-center gap-2 bg-[#17181c]/90 border border-[#333] px-2.5 py-1 rounded text-[11px] mono text-gray-300">
        <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span>3D glTF 2.0 Active · Bidirectional Selection Sync</span>
        {selectedElementId && (
          <span className="bg-indigo-900/60 border border-indigo-500/50 text-indigo-300 px-1.5 py-0.5 rounded text-[10px]">
            Selected: {selectedElementId}
          </span>
        )}
      </div>
    </div>
  )
}
