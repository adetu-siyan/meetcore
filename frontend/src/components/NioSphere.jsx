import { useEffect, useRef } from 'react'
import * as THREE from 'three'

/**
 * NioSphere — Three.js WebGL particle sphere
 *
 * States:
 *   idle      — slow revolving sphere, calm orange/white particles
 *   listening — sphere reacts to mic amplitude, particles spread outward
 *   processing — sphere flattens to a ring, particles cycle colors
 *   speaking  — sphere morphs and pulsates with speech energy
 */
export default function NioSphere({ state = 'idle', amplitude = 0 }) {
  const mountRef = useRef(null)
  const stateRef = useRef(state)
  const ampRef = useRef(amplitude)

  useEffect(() => { stateRef.current = state }, [state])
  useEffect(() => { ampRef.current = amplitude }, [amplitude])

  useEffect(() => {
    const el = mountRef.current
    if (!el) return

    // ── Renderer ──────────────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(el.clientWidth, el.clientHeight)
    renderer.setClearColor(0x000000, 0)
    el.appendChild(renderer.domElement)

    // ── Scene + Camera ────────────────────────────────────────────────────
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(60, el.clientWidth / el.clientHeight, 0.1, 100)
    camera.position.z = 3.5

    // ── Particles ─────────────────────────────────────────────────────────
    const COUNT = 4000
    const positions = new Float32Array(COUNT * 3)
    const colors = new Float32Array(COUNT * 3)
    const basePositions = new Float32Array(COUNT * 3) // original sphere positions
    const randoms = new Float32Array(COUNT)           // per-particle random offset

    const orange = new THREE.Color('#FF6719')
    const white = new THREE.Color('#ffffff')
    const gold = new THREE.Color('#ffd280')
    const blue = new THREE.Color('#93c5fd')

    for (let i = 0; i < COUNT; i++) {
      // Fibonacci sphere distribution — even spread
      const phi = Math.acos(1 - (2 * (i + 0.5)) / COUNT)
      const theta = Math.PI * (1 + Math.sqrt(5)) * i

      const x = Math.sin(phi) * Math.cos(theta)
      const y = Math.sin(phi) * Math.sin(theta)
      const z = Math.cos(phi)

      basePositions[i * 3]     = x
      basePositions[i * 3 + 1] = y
      basePositions[i * 3 + 2] = z

      positions[i * 3]     = x
      positions[i * 3 + 1] = y
      positions[i * 3 + 2] = z

      randoms[i] = Math.random()

      // Color: mostly orange-white gradient
      const c = i % 3 === 0 ? orange : i % 7 === 0 ? gold : white
      colors[i * 3]     = c.r
      colors[i * 3 + 1] = c.g
      colors[i * 3 + 2] = c.b
    }

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))

    const material = new THREE.PointsMaterial({
      size: 0.018,
      vertexColors: true,
      transparent: true,
      opacity: 0.92,
      sizeAttenuation: true,
    })

    const points = new THREE.Points(geometry, material)
    scene.add(points)

    // ── Animation ─────────────────────────────────────────────────────────
    let frame = 0
    let animId

    const animate = () => {
      animId = requestAnimationFrame(animate)
      frame++

      const t = frame * 0.01
      const s = stateRef.current
      const amp = ampRef.current

      const pos = geometry.attributes.position
      const col = geometry.attributes.color

      for (let i = 0; i < COUNT; i++) {
        const bx = basePositions[i * 3]
        const by = basePositions[i * 3 + 1]
        const bz = basePositions[i * 3 + 2]
        const r = randoms[i]

        let x = bx, y = by, z = bz
        let cr = white.r, cg = white.g, cb = white.b

        if (s === 'idle') {
          // Gentle breathing + slow rotation
          const breathe = 1 + 0.04 * Math.sin(t * 0.8 + r * Math.PI * 2)
          x = bx * breathe
          y = by * breathe
          z = bz * breathe

          const c = r < 0.6 ? orange : white
          cr = c.r; cg = c.g; cb = c.b

          // Slow Y rotation applied via sphere rotation (simpler)
          points.rotation.y = t * 0.15
          points.rotation.x = Math.sin(t * 0.08) * 0.1

        } else if (s === 'listening') {
          // Particles spread outward with mic amplitude
          const spread = 1 + amp * 0.6 + 0.05 * Math.sin(t * 2 + r * Math.PI * 4)
          x = bx * spread
          y = by * spread
          z = bz * spread

          // Orange intensity increases with amplitude
          const mix = Math.min(amp * 2, 1)
          cr = orange.r * mix + white.r * (1 - mix)
          cg = orange.g * mix + white.g * (1 - mix)
          cb = orange.b * mix + white.b * (1 - mix)

          points.rotation.y += 0.008

        } else if (s === 'processing') {
          // Flatten into ring — compress Y axis
          const flatFactor = 0.15 + 0.05 * Math.sin(t * 3 + r * 5)
          x = bx * (1 + 0.1 * Math.sin(t * 4 + r * Math.PI))
          y = by * flatFactor
          z = bz * (1 + 0.1 * Math.cos(t * 4 + r * Math.PI))

          // Cycle colors: orange → gold → blue → white
          const cycle = (t * 0.5 + r) % 1
          let c
          if (cycle < 0.33) c = orange
          else if (cycle < 0.66) c = gold
          else c = blue
          cr = c.r; cg = c.g; cb = c.b

          points.rotation.y += 0.025

        } else if (s === 'speaking') {
          // Pulsing morphs — wave across surface
          const pulse = 1 + 0.15 * Math.sin(t * 3 + r * Math.PI * 6) + 0.1 * amp
          const wave = 0.08 * Math.sin(t * 5 + bx * 4 + by * 4)
          x = bx * (pulse + wave)
          y = by * (pulse - wave * 0.5)
          z = bz * pulse

          // Warm orange-gold mix while speaking
          const mix = 0.5 + 0.5 * Math.sin(t * 2 + r * 3)
          cr = orange.r * mix + gold.r * (1 - mix)
          cg = orange.g * mix + gold.g * (1 - mix)
          cb = orange.b * mix + gold.b * (1 - mix)

          points.rotation.y += 0.01
        }

        pos.setXYZ(i, x, y, z)
        col.setXYZ(i, cr, cg, cb)
      }

      pos.needsUpdate = true
      col.needsUpdate = true

      renderer.render(scene, camera)
    }

    animate()

    // ── Resize ────────────────────────────────────────────────────────────
    const onResize = () => {
      if (!el) return
      renderer.setSize(el.clientWidth, el.clientHeight)
      camera.aspect = el.clientWidth / el.clientHeight
      camera.updateProjectionMatrix()
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', onResize)
      renderer.dispose()
      geometry.dispose()
      material.dispose()
      if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement)
    }
  }, []) // mount once

  return (
    <div
      ref={mountRef}
      className="w-full h-full"
      style={{ background: 'transparent' }}
    />
  )
}
