import { useEffect } from 'react'
import * as THREE from 'three'

export function FluidSphere({ canvasRef, amplitudeRef, sloshRef, dark }) {
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const W = canvas.offsetWidth  || 300
    const H = canvas.offsetHeight || 300

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(W, H)
    renderer.setClearColor(0x000000, 0)

    const scene  = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 100)
    camera.position.z = 2.8

    const vertexShader = `
      uniform float uTime;
      uniform float uAmp;
      uniform float uSloshX;
      uniform float uSloshY;
      varying vec3  vNormal;
      varying vec3  vViewDir;
      varying float vY;
      varying float vFresnel;

      float hash(float n) { return fract(sin(n) * 43758.5453); }
      float noise(vec3 p) {
        vec3 i = floor(p); vec3 f = fract(p);
        vec3 u = f * f * (3.0 - 2.0 * f);
        float n000 = hash(i.x + hash(i.y + hash(i.z)));
        float n100 = hash(i.x + 1.0 + hash(i.y + hash(i.z)));
        float n010 = hash(i.x + hash(i.y + 1.0 + hash(i.z)));
        float n110 = hash(i.x + 1.0 + hash(i.y + 1.0 + hash(i.z)));
        float n001 = hash(i.x + hash(i.y + hash(i.z + 1.0)));
        float n101 = hash(i.x + 1.0 + hash(i.y + hash(i.z + 1.0)));
        float n011 = hash(i.x + hash(i.y + 1.0 + hash(i.z + 1.0)));
        float n111 = hash(i.x + 1.0 + hash(i.y + 1.0 + hash(i.z + 1.0)));
        return mix(
          mix(mix(n000, n100, u.x), mix(n010, n110, u.x), u.y),
          mix(mix(n001, n101, u.x), mix(n011, n111, u.x), u.y), u.z);
      }

      void main() {
        vec3 norm  = normalize(normal);
        vNormal    = normalize(normalMatrix * norm);
        vY         = position.y;
        float equatorWeight = 1.0 - abs(position.y);
        vec3 sloshDisp = vec3(-uSloshX, -uSloshY, 0.0) * equatorWeight * 0.18;
        float n1 = noise(position * 1.2 + vec3(uTime * 0.20, uTime * 0.14, uTime * 0.17));
        float n2 = noise(position * 2.4 + vec3(uTime * 0.31, uTime * 0.25, uTime * 0.22)) * 0.5;
        float n3 = noise(position * 4.8 + vec3(uTime * 0.45, uTime * 0.38, uTime * 0.41)) * 0.25;
        float n  = (n1 + n2 + n3) / 1.75;
        float sloshMag = length(vec2(uSloshX, uSloshY));
        float disp = (n * 2.0 - 1.0) * (0.10 + uAmp * 0.35 + sloshMag * 0.12);
        vec3 displaced = position + norm * disp + sloshDisp;
        vec4 mvPos     = modelViewMatrix * vec4(displaced, 1.0);
        vViewDir       = normalize(-mvPos.xyz);
        float f        = 1.0 - abs(dot(vViewDir, vNormal));
        vFresnel       = pow(f, 2.0);
        gl_Position    = projectionMatrix * mvPos;
        float rimBoost = pow(vFresnel, 1.2);
        gl_PointSize   = (1.0 + rimBoost * 5.0) * (1.0 + uAmp * 1.2 + sloshMag * 0.4);
      }
    `

    const fragmentShaderDark = `
      varying float vY;
      varying float vFresnel;
      uniform float uAmp;

      void main() {
        vec2 uv = gl_PointCoord - 0.5;
        if (length(uv) > 0.5) discard;
        float soft = 1.0 - smoothstep(0.25, 0.5, length(uv));
        float t = clamp((vY + 1.0) * 0.5, 0.0, 1.0);
        vec3 cyan   = vec3(0.05, 0.85, 1.00);
        vec3 purple = vec3(0.70, 0.05, 0.90);
        vec3 orange = vec3(1.00, 0.35, 0.00);
        vec3 col = t > 0.5
          ? mix(purple, cyan,   (t - 0.5) * 2.0)
          : mix(orange, purple,  t * 2.0);
        float rimAlpha     = pow(vFresnel, 0.8);
        float interiorFade = 1.0 - pow(1.0 - vFresnel, 0.5) * 0.85;
        col = col * (0.3 + rimAlpha * 2.2 + uAmp * 1.0);
        gl_FragColor = vec4(col, soft * interiorFade * (0.5 + rimAlpha * 0.5));
      }
    `

    const fragmentShaderLight = `
      varying float vY;
      varying float vFresnel;
      uniform float uAmp;

      void main() {
        vec2 uv = gl_PointCoord - 0.5;
        if (length(uv) > 0.5) discard;
        float soft = 1.0 - smoothstep(0.1, 0.45, length(uv));
        float t = clamp((vY + 1.0) * 0.5, 0.0, 1.0);
        vec3 teal    = vec3(0.00, 0.72, 0.80);
        vec3 violet  = vec3(0.55, 0.10, 0.85);
        vec3 magenta = vec3(0.90, 0.10, 0.65);
        vec3 amber   = vec3(0.95, 0.55, 0.05);
        vec3 col;
        if (t > 0.66)      col = mix(violet,  teal,    (t - 0.66) * 3.0);
        else if (t > 0.33) col = mix(magenta, violet,  (t - 0.33) * 3.0);
        else               col = mix(amber,   magenta,  t * 3.0);
        float rimAlpha = pow(vFresnel, 0.6);
        col = col * (0.6 + rimAlpha * 0.5);
        gl_FragColor = vec4(col, soft * (0.55 + rimAlpha * 0.45) * (0.75 + uAmp * 0.5));
      }
    `

    const COUNT  = 12000
    const golden = Math.PI * (3.0 - Math.sqrt(5.0))
    const pos    = new Float32Array(COUNT * 3)
    const norms  = new Float32Array(COUNT * 3)
    for (let i = 0; i < COUNT; i++) {
      const y  = 1.0 - (i / (COUNT - 1)) * 2.0
      const r  = Math.sqrt(Math.max(0, 1.0 - y * y))
      const th = golden * i
      const x  = Math.cos(th) * r, z = Math.sin(th) * r
      pos[i * 3]     = x; pos[i * 3 + 1]     = y; pos[i * 3 + 2]     = z
      norms[i * 3]   = x; norms[i * 3 + 1]   = y; norms[i * 3 + 2]   = z
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(pos,   3))
    geo.setAttribute('normal',   new THREE.BufferAttribute(norms, 3))
    const uniforms = {
      uTime:   { value: 0 },
      uAmp:    { value: 0 },
      uSloshX: { value: 0 },
      uSloshY: { value: 0 },
    }
    const mat = new THREE.ShaderMaterial({
      uniforms,
      vertexShader,
      fragmentShader: dark ? fragmentShaderDark : fragmentShaderLight,
      transparent: true,
      blending: dark ? THREE.AdditiveBlending : THREE.NormalBlending,
      depthWrite: false,
    })
    const particles = new THREE.Points(geo, mat)
    scene.add(particles)

    const HALO   = 4000
    const hPos   = new Float32Array(HALO * 3)
    const hNorms = new Float32Array(HALO * 3)
    for (let i = 0; i < HALO; i++) {
      const y  = 1.0 - (i / (HALO - 1)) * 2.0
      const r  = Math.sqrt(Math.max(0, 1.0 - y * y))
      const th = golden * i
      const sc = 1.02 + Math.sin(i * 0.7) * 0.015
      const x  = Math.cos(th) * r, z = Math.sin(th) * r
      hPos[i * 3]     = x * sc; hPos[i * 3 + 1]     = y * sc; hPos[i * 3 + 2]     = z * sc
      hNorms[i * 3]   = x;      hNorms[i * 3 + 1]   = y;      hNorms[i * 3 + 2]   = z
    }
    const haloGeo = new THREE.BufferGeometry()
    haloGeo.setAttribute('position', new THREE.BufferAttribute(hPos,   3))
    haloGeo.setAttribute('normal',   new THREE.BufferAttribute(hNorms, 3))
    const hUniforms = {
      uTime:   { value: 0 },
      uAmp:    { value: 0 },
      uSloshX: { value: 0 },
      uSloshY: { value: 0 },
    }
    const haloMat = new THREE.ShaderMaterial({
      uniforms: hUniforms,
      vertexShader,
      fragmentShader: dark ? fragmentShaderDark : fragmentShaderLight,
      transparent: true,
      blending: dark ? THREE.AdditiveBlending : THREE.NormalBlending,
      depthWrite: false,
    })
    scene.add(new THREE.Points(haloGeo, haloMat))

    let frameId
    const clock = new THREE.Clock()
    const animate = () => {
      frameId = requestAnimationFrame(animate)
      const t   = clock.getElapsedTime()
      const amp = amplitudeRef.current || 0
      const sx  = sloshRef?.current?.x || 0
      const sy  = sloshRef?.current?.y || 0
      uniforms.uTime.value   = hUniforms.uTime.value   = t
      uniforms.uAmp.value    = hUniforms.uAmp.value    = amp
      uniforms.uSloshX.value = hUniforms.uSloshX.value = sx
      uniforms.uSloshY.value = hUniforms.uSloshY.value = sy

      particles.rotation.y = scene.children[1].rotation.y = t * 0.09
      particles.rotation.x = scene.children[1].rotation.x = Math.sin(t * 0.05) * 0.10
      renderer.render(scene, camera)
    }
    animate()

    const onResize = () => {
      const w = canvas.offsetWidth  || 300
      const h = canvas.offsetHeight || 300
      renderer.setSize(w, h)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    }
    window.addEventListener('resize', onResize)
    return () => {
      cancelAnimationFrame(frameId)
      window.removeEventListener('resize', onResize)
      renderer.dispose()
    }
  }, [dark, amplitudeRef, sloshRef])

  return <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
}
