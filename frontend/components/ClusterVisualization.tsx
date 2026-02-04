'use client'

import { useRef, useMemo, useState, useEffect, useCallback } from 'react'
import { Canvas, useFrame, useThree, extend } from '@react-three/fiber'
import { OrbitControls, Html, Line, Stars, PointMaterial, Points, PointerLockControls, PerspectiveCamera } from '@react-three/drei'
import * as THREE from 'three'
import { useStore, useSelection, useView } from '@/lib/store'
import type { Cluster, Term, Post } from '@/lib/api'

// Float mode state (global for simplicity)
let floatModeEnabled = false
let floatModeCallback: ((enabled: boolean) => void) | null = null

// Color palette for elegant scientific look
const COLORS = {
  primary: '#00d4ff',    // Cyan
  secondary: '#ff6b9d',  // Pink
  tertiary: '#a855f7',   // Purple
  accent: '#fbbf24',     // Gold/Yellow
  background: '#050510', // Deep space black
  grid: '#1a1a3a',       // Subtle grid
}

// Label styles
const labelStyle: React.CSSProperties = {
  background: 'rgba(5, 5, 20, 0.9)',
  backdropFilter: 'blur(12px)',
  border: '1px solid rgba(0, 212, 255, 0.4)',
  borderRadius: '8px',
  padding: '8px 14px',
  color: '#fff',
  fontSize: '12px',
  fontWeight: 500,
  fontFamily: 'ui-monospace, monospace',
  whiteSpace: 'nowrap',
  pointerEvents: 'none',
  boxShadow: '0 0 20px rgba(0, 212, 255, 0.2)',
}

const clusterLabelStyle: React.CSSProperties = {
  ...labelStyle,
  border: '1px solid rgba(255, 107, 157, 0.5)',
  boxShadow: '0 0 25px rgba(255, 107, 157, 0.25)',
  padding: '10px 16px',
}

// Wireframe cube boundary
function BoundingCube({ size = 12 }: { size?: number }) {
  const edges = useMemo(() => {
    const s = size / 2
    const vertices = [
      // Bottom face
      [[-s, -s, -s], [s, -s, -s]],
      [[s, -s, -s], [s, -s, s]],
      [[s, -s, s], [-s, -s, s]],
      [[-s, -s, s], [-s, -s, -s]],
      // Top face
      [[-s, s, -s], [s, s, -s]],
      [[s, s, -s], [s, s, s]],
      [[s, s, s], [-s, s, s]],
      [[-s, s, s], [-s, s, -s]],
      // Vertical edges
      [[-s, -s, -s], [-s, s, -s]],
      [[s, -s, -s], [s, s, -s]],
      [[s, -s, s], [s, s, s]],
      [[-s, -s, s], [-s, s, s]],
    ]
    return vertices
  }, [size])

  return (
    <group>
      {edges.map((edge, i) => (
        <Line
          key={i}
          points={edge as [number, number, number][]}
          color={COLORS.grid}
          lineWidth={1}
          transparent
          opacity={0.3}
        />
      ))}
    </group>
  )
}

// Subtle grid planes
function GridPlanes({ size = 12 }: { size?: number }) {
  return (
    <group>
      {/* Bottom grid */}
      <gridHelper
        args={[size, 20, COLORS.grid, COLORS.grid]}
        position={[0, -size / 2, 0]}
        rotation={[0, 0, 0]}
      />
    </group>
  )
}

// Glowing data point
function DataPoint({ term, isSelected, isHovered, onClick, onHover, colorValue, showLabels, pointSize }: {
  term: Term
  isSelected: boolean
  isHovered: boolean
  onClick: () => void
  onHover: (hovered: boolean) => void
  colorValue: number // 0-1 for color gradient
  showLabels: boolean
  pointSize: number
}) {
  const meshRef = useRef<THREE.Mesh>(null)
  const glowRef = useRef<THREE.Mesh>(null)

  // Color based on trend/value - cyan to pink gradient
  const baseColor = useMemo(() => {
    const c = new THREE.Color()
    c.setHSL(0.55 - colorValue * 0.4, 0.9, 0.6) // Cyan to pink
    return c
  }, [colorValue])

  useFrame(({ clock }) => {
    if (meshRef.current) {
      const scale = isSelected ? 2 : isHovered ? 1.6 : 1
      meshRef.current.scale.lerp(new THREE.Vector3(scale, scale, scale), 0.15)
    }
    if (glowRef.current) {
      // Subtle pulse
      const pulse = 1 + Math.sin(clock.getElapsedTime() * 2 + colorValue * 10) * 0.1
      glowRef.current.scale.setScalar(isSelected ? 3 * pulse : isHovered ? 2.5 * pulse : 1.8 * pulse)
    }
  })

  const pointColor = isSelected ? COLORS.accent : isHovered ? COLORS.secondary : baseColor

  const baseSize = 0.06 * pointSize
  const glowSize = 0.12 * pointSize

  return (
    <group position={[term.x, term.y, term.z]}>
      {/* Glow sphere */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[glowSize, 16, 16]} />
        <meshBasicMaterial
          color={pointColor}
          transparent
          opacity={0.15}
        />
      </mesh>

      {/* Core point */}
      <mesh
        ref={meshRef}
        onClick={(e) => { e.stopPropagation(); onClick() }}
        onPointerOver={(e) => { e.stopPropagation(); onHover(true) }}
        onPointerOut={() => onHover(false)}
      >
        <sphereGeometry args={[baseSize, 16, 16]} />
        <meshBasicMaterial color={pointColor} />
      </mesh>

      {/* Label */}
      {showLabels && (isHovered || isSelected) && (
        <Html center zIndexRange={[100, 200]} style={{ transform: 'translateY(-25px)' }}>
          <div style={labelStyle}>
            <div style={{ color: COLORS.primary, marginBottom: '2px' }}>{term.term}</div>
            {term.category && (
              <div style={{ fontSize: '10px', color: '#888', textTransform: 'uppercase' }}>
                {term.category.replace(/_/g, ' ')}
              </div>
            )}
          </div>
        </Html>
      )}
    </group>
  )
}

// Cluster marker - glowing orb (decorative, doesn't block clicks)
function ClusterOrb({ cluster, isSelected, isHovered, onClick, onHover }: {
  cluster: Cluster
  isSelected: boolean
  isHovered: boolean
  onClick: () => void
  onHover: (hovered: boolean) => void
}) {
  const groupRef = useRef<THREE.Group>(null)
  const innerRef = useRef<THREE.Mesh>(null)

  const clusterColor = useMemo(() => {
    return cluster.color || COLORS.secondary
  }, [cluster.color])

  // Disable raycasting on decorative meshes
  const noRaycast = useCallback(() => {}, [])

  useFrame(({ clock }) => {
    if (groupRef.current) {
      // Gentle rotation
      groupRef.current.rotation.y = clock.getElapsedTime() * 0.1
    }
    if (innerRef.current) {
      const scale = isSelected ? 1.4 : isHovered ? 1.2 : 1
      innerRef.current.scale.lerp(new THREE.Vector3(scale, scale, scale), 0.1)
    }
  })

  const displayName = cluster.name.length > 30
    ? cluster.name.substring(0, 30) + '...'
    : cluster.name

  const orbSize = 0.3 + (cluster.termCount || 1) * 0.02

  return (
    <group position={[cluster.x, cluster.y, cluster.z]} ref={groupRef}>
      {/* Outer glow rings - decorative only, no raycast */}
      <mesh rotation={[Math.PI / 2, 0, 0]} raycast={noRaycast}>
        <ringGeometry args={[orbSize * 1.5, orbSize * 1.8, 32]} />
        <meshBasicMaterial
          color={clusterColor}
          transparent
          opacity={isSelected ? 0.4 : isHovered ? 0.3 : 0.15}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Inner orb - decorative only, no raycast */}
      <mesh ref={innerRef} raycast={noRaycast}>
        <icosahedronGeometry args={[orbSize, 1]} />
        <meshBasicMaterial
          color={clusterColor}
          transparent
          opacity={isSelected ? 0.9 : isHovered ? 0.7 : 0.5}
          wireframe={!isSelected && !isHovered}
        />
      </mesh>

      {/* Small clickable core marker - this IS clickable */}
      <mesh
        onClick={(e) => { e.stopPropagation(); onClick() }}
        onPointerOver={(e) => { e.stopPropagation(); onHover(true) }}
        onPointerOut={() => onHover(false)}
      >
        <sphereGeometry args={[orbSize * 0.3, 16, 16]} />
        <meshBasicMaterial color={clusterColor} transparent opacity={0} />
      </mesh>

      {/* Label */}
      {(isHovered || isSelected) && (
        <Html center position={[0, orbSize + 0.5, 0]} zIndexRange={[200, 300]}>
          <div style={clusterLabelStyle}>
            <div style={{ color: COLORS.secondary, fontWeight: 600, marginBottom: '4px' }}>
              {displayName}
            </div>
            <div style={{ fontSize: '10px', color: '#aaa' }}>
              {cluster.termCount} terms
            </div>
          </div>
        </Html>
      )}
    </group>
  )
}

// Elegant connection lines with gradient
function DataConnections({ terms, clusters }: { terms: Term[]; clusters: Cluster[] }) {
  const lines = useMemo(() => {
    const result: Array<{ points: [number, number, number][]; color: string }> = []

    terms.forEach((term) => {
      if (term.clusterId) {
        const cluster = clusters.find((c) => c.id === term.clusterId)
        if (cluster) {
          result.push({
            points: [
              [term.x, term.y, term.z],
              [cluster.x, cluster.y, cluster.z],
            ],
            color: cluster.color || COLORS.primary,
          })
        }
      }
    })

    return result
  }, [terms, clusters])

  return (
    <group>
      {lines.map((line, i) => (
        <Line
          key={i}
          points={line.points}
          color={line.color}
          lineWidth={0.5}
          transparent
          opacity={0.2}
        />
      ))}
    </group>
  )
}

// Ambient particles for depth - like stars
function AmbientParticles({ count = 800 }: { count?: number }) {
  const points = useMemo(() => {
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)

    for (let i = 0; i < count; i++) {
      // Spread particles in a sphere around the scene
      const radius = 15 + Math.random() * 20
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)

      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = radius * Math.cos(phi)

      // Subtle color variation
      const color = new THREE.Color()
      color.setHSL(0.55 + Math.random() * 0.1, 0.3, 0.5 + Math.random() * 0.3)
      colors[i * 3] = color.r
      colors[i * 3 + 1] = color.g
      colors[i * 3 + 2] = color.b
    }

    return { positions, colors }
  }, [count])

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={count} array={points.positions} itemSize={3} />
        <bufferAttribute attach="attributes-color" count={count} array={points.colors} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.03} vertexColors transparent opacity={0.6} sizeAttenuation />
    </points>
  )
}

// Fly-through controls for immersive navigation
function FlyControls({ enabled }: { enabled: boolean }) {
  const { camera, gl } = useThree()
  const moveState = useRef({ forward: false, backward: false, left: false, right: false, up: false, down: false })
  const velocity = useRef(new THREE.Vector3())
  const direction = useRef(new THREE.Vector3())
  const euler = useRef(new THREE.Euler(0, 0, 0, 'YXZ'))
  const isLocked = useRef(false)

  const speed = 0.15
  const damping = 0.92

  useEffect(() => {
    if (!enabled) return

    const onKeyDown = (e: KeyboardEvent) => {
      switch (e.code) {
        case 'KeyW': case 'ArrowUp': moveState.current.forward = true; break
        case 'KeyS': case 'ArrowDown': moveState.current.backward = true; break
        case 'KeyA': case 'ArrowLeft': moveState.current.left = true; break
        case 'KeyD': case 'ArrowRight': moveState.current.right = true; break
        case 'Space': moveState.current.up = true; break
        case 'ShiftLeft': moveState.current.down = true; break
      }
    }

    const onKeyUp = (e: KeyboardEvent) => {
      switch (e.code) {
        case 'KeyW': case 'ArrowUp': moveState.current.forward = false; break
        case 'KeyS': case 'ArrowDown': moveState.current.backward = false; break
        case 'KeyA': case 'ArrowLeft': moveState.current.left = false; break
        case 'KeyD': case 'ArrowRight': moveState.current.right = false; break
        case 'Space': moveState.current.up = false; break
        case 'ShiftLeft': moveState.current.down = false; break
      }
    }

    const onMouseMove = (e: MouseEvent) => {
      if (!isLocked.current) return

      euler.current.setFromQuaternion(camera.quaternion)
      euler.current.y -= e.movementX * 0.002
      euler.current.x -= e.movementY * 0.002
      euler.current.x = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, euler.current.x))
      camera.quaternion.setFromEuler(euler.current)
    }

    const onPointerLockChange = () => {
      isLocked.current = document.pointerLockElement === gl.domElement
    }

    const onClick = () => {
      if (enabled && !isLocked.current) {
        gl.domElement.requestPointerLock()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup', onKeyUp)
    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('pointerlockchange', onPointerLockChange)
    gl.domElement.addEventListener('click', onClick)

    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup', onKeyUp)
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('pointerlockchange', onPointerLockChange)
      gl.domElement.removeEventListener('click', onClick)
      if (document.pointerLockElement) {
        document.exitPointerLock()
      }
    }
  }, [enabled, camera, gl])

  useFrame(() => {
    if (!enabled) return

    direction.current.set(0, 0, 0)

    if (moveState.current.forward) direction.current.z -= 1
    if (moveState.current.backward) direction.current.z += 1
    if (moveState.current.left) direction.current.x -= 1
    if (moveState.current.right) direction.current.x += 1
    if (moveState.current.up) direction.current.y += 1
    if (moveState.current.down) direction.current.y -= 1

    direction.current.normalize()
    direction.current.applyQuaternion(camera.quaternion)

    velocity.current.add(direction.current.multiplyScalar(speed))
    velocity.current.multiplyScalar(damping)

    camera.position.add(velocity.current)
  })

  return null
}

// Dynamic fly-through tour - zooms through the data dramatically
function AutoPilot({ enabled, terms }: { enabled: boolean; terms: Term[] }) {
  const { camera } = useThree()
  const progressRef = useRef(0)
  const waypointsRef = useRef<THREE.Vector3[]>([])
  const centerRef = useRef(new THREE.Vector3(0, 0, 0))

  // Generate exciting waypoints through the data
  useEffect(() => {
    if (terms.length < 3) return

    // Calculate center
    const center = new THREE.Vector3()
    terms.forEach(t => center.add(new THREE.Vector3(t.x, t.y, t.z)))
    center.divideScalar(terms.length)
    centerRef.current = center

    // Pick diverse waypoints - spread across different areas
    const waypoints: THREE.Vector3[] = []
    const shuffled = [...terms].sort(() => Math.random() - 0.5)

    // Start with a dramatic pullback view
    waypoints.push(new THREE.Vector3(center.x, center.y + 3, center.z + 12))

    // Dive into the data - pick 8-12 points to fly between
    const numWaypoints = Math.min(12, Math.max(8, Math.floor(terms.length / 10)))
    for (let i = 0; i < numWaypoints; i++) {
      const term = shuffled[i]
      // Position camera close to data point, slightly offset for drama
      const offset = new THREE.Vector3(
        (Math.random() - 0.5) * 1.5,
        (Math.random() - 0.5) * 1.5 + 0.5,
        Math.random() * 2 + 1 // Always slightly in front
      )
      waypoints.push(new THREE.Vector3(term.x + offset.x, term.y + offset.y, term.z + offset.z))
    }

    // Add some dramatic sweeping moves through clusters
    const extremes = {
      minX: Math.min(...terms.map(t => t.x)),
      maxX: Math.max(...terms.map(t => t.x)),
      minY: Math.min(...terms.map(t => t.y)),
      maxY: Math.max(...terms.map(t => t.y)),
      minZ: Math.min(...terms.map(t => t.z)),
      maxZ: Math.max(...terms.map(t => t.z)),
    }

    // Sweeping corner-to-corner moves
    waypoints.push(new THREE.Vector3(extremes.minX - 1, center.y + 2, extremes.maxZ + 3))
    waypoints.push(new THREE.Vector3(extremes.maxX + 1, extremes.maxY + 1, center.z))
    waypoints.push(new THREE.Vector3(center.x, extremes.minY - 1, extremes.minZ - 2))

    // End with a pullback reveal
    waypoints.push(new THREE.Vector3(center.x + 5, center.y + 5, center.z + 15))

    waypointsRef.current = waypoints
    progressRef.current = 0
  }, [terms])

  useFrame((_, delta) => {
    if (!enabled || waypointsRef.current.length < 4) return

    const waypoints = waypointsRef.current
    const speed = 0.08 // Adjust for faster/slower tour
    progressRef.current += delta * speed

    // Loop through waypoints
    const totalSegments = waypoints.length
    const t = progressRef.current % totalSegments
    const segmentIndex = Math.floor(t)
    const segmentProgress = t - segmentIndex

    // Get 4 points for Catmull-Rom interpolation (smooth curves)
    const p0 = waypoints[(segmentIndex - 1 + totalSegments) % totalSegments]
    const p1 = waypoints[segmentIndex % totalSegments]
    const p2 = waypoints[(segmentIndex + 1) % totalSegments]
    const p3 = waypoints[(segmentIndex + 2) % totalSegments]

    // Catmull-Rom spline for buttery smooth movement
    const f = segmentProgress
    const f2 = f * f
    const f3 = f2 * f

    const targetPos = new THREE.Vector3(
      0.5 * (2 * p1.x + (-p0.x + p2.x) * f + (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * f2 + (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * f3),
      0.5 * (2 * p1.y + (-p0.y + p2.y) * f + (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * f2 + (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * f3),
      0.5 * (2 * p1.z + (-p0.z + p2.z) * f + (2 * p0.z - 5 * p1.z + 4 * p2.z - p3.z) * f2 + (-p0.z + 3 * p1.z - 3 * p2.z + p3.z) * f3)
    )

    // Smooth camera movement
    camera.position.lerp(targetPos, 0.06)

    // Look ahead in the direction of travel for cinematic feel
    const lookAheadT = (t + 0.3) % totalSegments
    const lookSegment = Math.floor(lookAheadT)
    const lookProgress = lookAheadT - lookSegment

    const lp0 = waypoints[(lookSegment - 1 + totalSegments) % totalSegments]
    const lp1 = waypoints[lookSegment % totalSegments]
    const lp2 = waypoints[(lookSegment + 1) % totalSegments]
    const lp3 = waypoints[(lookSegment + 2) % totalSegments]

    const lf = lookProgress
    const lf2 = lf * lf
    const lf3 = lf2 * lf

    const lookTarget = new THREE.Vector3(
      0.5 * (2 * lp1.x + (-lp0.x + lp2.x) * lf + (2 * lp0.x - 5 * lp1.x + 4 * lp2.x - lp3.x) * lf2 + (-lp0.x + 3 * lp1.x - 3 * lp2.x + lp3.x) * lf3),
      0.5 * (2 * lp1.y + (-lp0.y + lp2.y) * lf + (2 * lp0.y - 5 * lp1.y + 4 * lp2.y - lp3.y) * lf2 + (-lp0.y + 3 * lp1.y - 3 * lp2.y + lp3.y) * lf3),
      0.5 * (2 * lp1.z + (-lp0.z + lp2.z) * lf + (2 * lp0.z - 5 * lp1.z + 4 * lp2.z - lp3.z) * lf2 + (-lp0.z + 3 * lp1.z - 3 * lp2.z + lp3.z) * lf3)
    )

    // Smooth rotation towards look target
    const targetQuat = new THREE.Quaternion()
    const lookMatrix = new THREE.Matrix4()
    lookMatrix.lookAt(camera.position, lookTarget, new THREE.Vector3(0, 1, 0))
    targetQuat.setFromRotationMatrix(lookMatrix)
    camera.quaternion.slerp(targetQuat, 0.04)
  })

  return null
}

// Camera controller
function CameraController({ floatMode }: { floatMode: boolean }) {
  const { camera } = useThree()
  const view = useView()
  const targetRef = useRef<THREE.Vector3>(new THREE.Vector3(...view.cameraPosition))
  const isAnimatingRef = useRef(false)
  const lastTargetRef = useRef<string>(view.cameraPosition.join(','))

  useEffect(() => {
    if (floatMode) return // Don't control camera in float mode

    const newTarget = view.cameraPosition.join(',')
    if (newTarget !== lastTargetRef.current) {
      targetRef.current.set(...view.cameraPosition)
      isAnimatingRef.current = true
      lastTargetRef.current = newTarget
    }
  }, [view.cameraPosition, floatMode])

  useFrame(() => {
    if (floatMode) return

    if (isAnimatingRef.current) {
      camera.position.lerp(targetRef.current, 0.08)
      if (camera.position.distanceTo(targetRef.current) < 0.1) {
        isAnimatingRef.current = false
      }
    }
  })

  return null
}

// Main scene
function Scene({ floatMode, autoPilot }: { floatMode: boolean; autoPilot: boolean }) {
  const clusters = useStore((s) => s.clusters)
  const allTerms = useStore((s) => s.terms)
  const filters = useStore((s) => s.filters)
  const selection = useSelection()
  const view = useView()
  const selectAndFocusTerm = useStore((s) => s.selectAndFocusTerm)
  const selectAndFocusCluster = useStore((s) => s.selectAndFocusCluster)
  const setHoveredTerm = useStore((s) => s.setHoveredTerm)
  const [hoveredClusterId, setHoveredClusterId] = useState<number | null>(null)

  // Filter terms
  const terms = useMemo(() => {
    let filtered = allTerms

    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase()
      filtered = filtered.filter((term) =>
        term.term.toLowerCase().includes(query) ||
        (term.category && term.category.toLowerCase().includes(query))
      )
    }

    if (filters.category) {
      filtered = filtered.filter((term) =>
        term.category?.toLowerCase() === filters.category?.toLowerCase()
      )
    }

    if (filters.clusterId) {
      filtered = filtered.filter((term) => term.clusterId === filters.clusterId)
    }

    return filtered
  }, [allTerms, filters.searchQuery, filters.category, filters.clusterId])

  // Filter clusters
  const filteredClusters = useMemo(() => {
    if (!filters.searchQuery && !filters.category) return clusters
    const termClusterIds = new Set(terms.map((t) => t.clusterId))
    return clusters.filter((c) => termClusterIds.has(c.id))
  }, [clusters, terms, filters.searchQuery, filters.category])

  // Calculate color values for gradient (based on index for now)
  const termColorValues = useMemo(() => {
    const values = new Map<number, number>()
    terms.forEach((term, i) => {
      values.set(term.id, i / Math.max(terms.length - 1, 1))
    })
    return values
  }, [terms])

  return (
    <>
      <CameraController floatMode={floatMode || autoPilot} />
      <FlyControls enabled={floatMode} />
      <AutoPilot enabled={autoPilot} terms={terms} />

      {/* Background elements */}
      <AmbientParticles count={600} />
      <BoundingCube size={14} />
      <GridPlanes size={14} />

      {/* Data: Clusters */}
      {filteredClusters.map((cluster) => (
        <ClusterOrb
          key={cluster.id}
          cluster={cluster}
          isSelected={selection.selectedCluster?.id === cluster.id}
          isHovered={hoveredClusterId === cluster.id}
          onClick={() => selectAndFocusCluster(cluster)}
          onHover={(h) => setHoveredClusterId(h ? cluster.id : null)}
        />
      ))}

      {/* Data: Terms */}
      {terms.map((term) => (
        <DataPoint
          key={term.id}
          term={term}
          isSelected={selection.selectedTerm?.id === term.id}
          isHovered={selection.hoveredTerm?.id === term.id}
          onClick={() => selectAndFocusTerm(term)}
          onHover={(h) => setHoveredTerm(h ? term : null)}
          colorValue={termColorValues.get(term.id) || 0}
          showLabels={view.showLabels}
          pointSize={view.pointSize}
        />
      ))}

      {/* Connections */}
      {view.showConnections && <DataConnections terms={terms} clusters={filteredClusters} />}
    </>
  )
}

// Main component
export default function ClusterVisualization() {
  const [floatMode, setFloatMode] = useState(false)
  const [autoPilot, setAutoPilot] = useState(false)

  const toggleFloatMode = () => {
    setFloatMode(!floatMode)
    setAutoPilot(false)
  }

  const toggleAutoPilot = () => {
    setAutoPilot(!autoPilot)
    setFloatMode(false)
  }

  return (
    <div className="canvas-container" style={{ background: COLORS.background }}>
      <Canvas
        camera={{ position: [0, 5, 18], fov: 55 }}
        gl={{ antialias: true, alpha: false }}
      >
        <color attach="background" args={[COLORS.background]} />

        {/* Minimal lighting - let meshBasicMaterial glow */}
        <ambientLight intensity={0.2} />

        <Scene floatMode={floatMode} autoPilot={autoPilot} />

        {!floatMode && !autoPilot && (
          <OrbitControls
            enableDamping
            dampingFactor={0.05}
            rotateSpeed={0.4}
            zoomSpeed={0.8}
            minDistance={3}
            maxDistance={40}
            enablePan={true}
            panSpeed={0.5}
            autoRotate={false}
          />
        )}
      </Canvas>

      {/* Float mode controls */}
      <div
        style={{
          position: 'absolute',
          bottom: 20,
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          gap: 10,
          zIndex: 50,
        }}
      >
        <button
          onClick={toggleAutoPilot}
          style={{
            background: autoPilot ? COLORS.primary : 'rgba(5, 5, 20, 0.8)',
            border: `1px solid ${autoPilot ? COLORS.primary : 'rgba(0, 212, 255, 0.4)'}`,
            borderRadius: 8,
            padding: '10px 20px',
            color: '#fff',
            fontSize: 13,
            fontFamily: 'ui-monospace, monospace',
            cursor: 'pointer',
            backdropFilter: 'blur(8px)',
            transition: 'all 0.2s',
          }}
        >
          {autoPilot ? '⏸ Stop Tour' : '🚀 Auto Tour'}
        </button>
        <button
          onClick={toggleFloatMode}
          style={{
            background: floatMode ? COLORS.secondary : 'rgba(5, 5, 20, 0.8)',
            border: `1px solid ${floatMode ? COLORS.secondary : 'rgba(255, 107, 157, 0.4)'}`,
            borderRadius: 8,
            padding: '10px 20px',
            color: '#fff',
            fontSize: 13,
            fontFamily: 'ui-monospace, monospace',
            cursor: 'pointer',
            backdropFilter: 'blur(8px)',
            transition: 'all 0.2s',
          }}
        >
          {floatMode ? '🔓 Exit Float' : '🎮 Float Mode'}
        </button>
      </div>

      {/* Float mode instructions */}
      {floatMode && (
        <div
          style={{
            position: 'absolute',
            top: 20,
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(5, 5, 20, 0.9)',
            border: '1px solid rgba(255, 107, 157, 0.4)',
            borderRadius: 8,
            padding: '12px 20px',
            color: '#fff',
            fontSize: 12,
            fontFamily: 'ui-monospace, monospace',
            zIndex: 50,
            textAlign: 'center',
          }}
        >
          <div style={{ marginBottom: 4, color: COLORS.secondary }}>🎮 FLOAT MODE</div>
          <div style={{ color: '#aaa' }}>
            Click to lock mouse • <b>WASD</b> move • <b>Mouse</b> look • <b>Space/Shift</b> up/down • <b>ESC</b> unlock
          </div>
        </div>
      )}

      {autoPilot && (
        <div
          style={{
            position: 'absolute',
            top: 20,
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(5, 5, 20, 0.9)',
            border: '1px solid rgba(0, 212, 255, 0.4)',
            borderRadius: 8,
            padding: '12px 20px',
            color: '#fff',
            fontSize: 12,
            fontFamily: 'ui-monospace, monospace',
            zIndex: 50,
            textAlign: 'center',
          }}
        >
          <div style={{ marginBottom: 4, color: COLORS.primary }}>🚀 AUTO TOUR</div>
          <div style={{ color: '#aaa' }}>Drifting through the data... Click button to stop</div>
        </div>
      )}

      {/* Gradient overlay at edges for depth */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          background: 'radial-gradient(ellipse at center, transparent 50%, rgba(5,5,16,0.4) 100%)',
        }}
      />
    </div>
  )
}
