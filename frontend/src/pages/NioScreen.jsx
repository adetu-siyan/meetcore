import { useEffect, useRef, useState, useCallback } from 'react'
import * as THREE from 'three'
import { PanelShell } from '../components/PanelShell'
import { TranscriptPanel } from '../components/TranscriptPanel'
import { SummaryPanel } from '../components/SummaryPanel'
import { ActionItemsPanel } from '../components/ActionItemsPanel'
import { DraftEmailPanel } from '../components/DraftEmailPanel'
import { CalendarPanel } from '../components/CalendarPanel'
import { SettingsModal } from '../components/SettingsModal'

const API = import.meta.env.VITE_API_URL

function prepareSpeechText(text) {
  if (!text) return ''
  return text
    .replace(/\.+/g, ',')
    .replace(/\n+/g, ', ')
    .replace(/(\.{2,}|—|–)/g, ' ')
    .replace(/[:;]/g, ' ')
    .replace(/,\s*,+/g, ',')
    .replace(/,\s*$/g, '')
    .trim()
}

const TOOL_ICONS = {
  get_transcript: (color) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"
        stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"
        stroke={color} strokeWidth="1.8" strokeLinecap="round"/>
    </svg>
  ),
  summarize_meeting: (color) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"
        stroke={color} strokeWidth="1.8" strokeLinecap="round"/>
    </svg>
  ),
  action_items: (color) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M9 11l3 3L22 4"
        stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"
        stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  draft_email: (color) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"
        stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M22 6l-10 7L2 6"
        stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  schedule_meeting: (color) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <line x1="16" y1="2" x2="16" y2="6" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <line x1="8" y1="2" x2="8" y2="6" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <line x1="3" y1="10" x2="21" y2="10" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
}

const ENDPOINTS = {
  get_transcript:    '/tools/transcript',
  summarize_meeting: '/tools/summary',
  action_items:      '/tools/action-items',
  draft_email:       '/tools/draft-email',
  schedule_meeting:  '/tools/schedule-meeting',
}

// ── Audio Helpers ─────────────────────────────────────────────────────────────

async function fetchAudioBuffer(text, voice, audioCtx) {
  if (!text?.trim()) return null
  try {
    const res = await fetch(`${API}/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice }),
    })
    if (!res.ok) return null
    const arrayBuffer = await res.arrayBuffer()
    if (!arrayBuffer.byteLength) return null
    return await audioCtx.decodeAudioData(arrayBuffer)
  } catch (e) {
    console.warn('[TTS] fetch/decode error:', e)
    return null
  }
}

function playDecodedBuffer(buffer, audioCtx, amplitudeRef, shouldStop) {
  return new Promise((resolve) => {
    if (!buffer || shouldStop()) { resolve(); return }
    const source   = audioCtx.createBufferSource()
    source.buffer  = buffer
    const analyser = audioCtx.createAnalyser()
    analyser.fftSize = 256
    source.connect(analyser)
    analyser.connect(audioCtx.destination)
    const data = new Uint8Array(analyser.frequencyBinCount)
    let isPlaying = true
    const readAmp = () => {
      if (!isPlaying || shouldStop()) return
      analyser.getByteFrequencyData(data)
      amplitudeRef.current = Math.min(
        data.reduce((a, b) => a + b, 0) / data.length / 80, 1
      )
      requestAnimationFrame(readAmp)
    }
    readAmp()
    source.onended = () => {
      isPlaying = false
      amplitudeRef.current = 0
      resolve()
    }
    source.start(0)
  })
}



// ── FluidSphere (Commented-Out Architecture & Shaders) ────────────────────────


// ── Main Screen ───────────────────────────────────────────────────────────────

export default function NioScreen({ meetingId, onEnd }) {
  const [phase, setPhase]           = useState('idle')
  const [caption, setCaption]       = useState('')
  const [recording, setRecording]   = useState(false)
  const [error, setError]           = useState('')
  const [dark, setDark]             = useState(false)
  const [activeTool, setActiveTool] = useState(null)
  const [usedTools, setUsedTools]   = useState([])
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [toolData, setToolData]     = useState({
    get_transcript:    { status: 'idle', content: null },
    summarize_meeting: { status: 'idle', content: null },
    action_items:      { status: 'idle', content: null },
    draft_email:       { status: 'idle', content: null },
    schedule_meeting:  { status: 'idle', content: null },
  })

  const canvasRef    = useRef(null)
  const amplitudeRef = useRef(0)
  const audioCtxRef  = useRef(null)
  const mediaRef     = useRef(null)
  const chunksRef    = useRef([])
  const historyRef   = useRef([])
  const ampRafRef    = useRef(null)
  const bgRef        = useRef(null)
  const phaseRef     = useRef('idle')
  const speakingRef  = useRef(false)
  const stopAudioRef = useRef(false)
  const toolRunning  = useRef(false)
  const sloshRef     = useRef({ x: 0, y: 0 })
  const sloshVelRef  = useRef({ x: 0, y: 0 })

  const panelOpen  = activeTool !== null
  const activeAxis = panelOpen ? 'calc(50% + 220px)' : '50%'

  // ── Slosh spring ────────────────────────────────────────────────────────────
  useEffect(() => {
    const STIFFNESS = 110, DAMPING = 11, MASS = 1
    let rafId, lastT = performance.now()
    const tick = () => {
      const now = performance.now(), dt = Math.min((now - lastT) / 1000, 0.05)
      lastT = now
      const spring = (val, vel, target) => {
        const force = -STIFFNESS * (val - target), damp = -DAMPING * vel
        const accel = (force + damp) / MASS, newVel = vel + accel * dt
        return { val: val + newVel * dt, vel: newVel }
      }
      const rx = spring(sloshRef.current.x, sloshVelRef.current.x, 0)
      const ry = spring(sloshRef.current.y, sloshVelRef.current.y, 0)
      sloshRef.current    = { x: rx.val, y: ry.val }
      sloshVelRef.current = { x: rx.vel, y: ry.vel }
      rafId = requestAnimationFrame(tick)
    }
    rafId = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafId)
  }, [])

  const prevPanelOpen = useRef(false)
  useEffect(() => {
    const opening = panelOpen  && !prevPanelOpen.current
    const closing = !panelOpen && prevPanelOpen.current
    prevPanelOpen.current = panelOpen
    if (opening) sloshVelRef.current.x -= 1.8
    else if (closing) sloshVelRef.current.x += 1.8
  }, [panelOpen])

  useEffect(() => { phaseRef.current = phase }, [phase])

  useEffect(() => {
    const tick = () => {
      if (bgRef.current) bgRef.current.style.opacity = 0.4 + (amplitudeRef.current || 0) * 0.5
      ampRafRef.current = requestAnimationFrame(tick)
    }
    ampRafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(ampRafRef.current)
  }, [])

  useEffect(() => {
    if (phase !== 'thinking') return
    let t = 0
    const id = setInterval(() => {
      t += 0.08
      amplitudeRef.current = 0.15 + Math.sin(t) * 0.1
    }, 50)
    return () => clearInterval(id)
  }, [phase])

  // ── speakText ───────────────────────────────────────────────────────────────
  const speakText = useCallback(async (text) => {
    const cleanedText = prepareSpeechText(text)
    // Guard against empty strings or blank space preventing 422 Unprocessable Entity
    if (!cleanedText || !cleanedText.trim()) {
      return
    }

    if (speakingRef.current) {
      stopAudioRef.current = true
      await new Promise(r => setTimeout(r, 60))
    }
    speakingRef.current  = true
    stopAudioRef.current = false
    setPhase('speaking')
    setError('')
    if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
      audioCtxRef.current = new AudioContext()
    }
    if (audioCtxRef.current.state === 'suspended') await audioCtxRef.current.resume()
    const ctx = audioCtxRef.current

    const audioBuffer = await fetchAudioBuffer(cleanedText, 'hannah', ctx)
    if (audioBuffer && !stopAudioRef.current) {
      await playDecodedBuffer(audioBuffer, ctx, amplitudeRef, () => stopAudioRef.current)
    }
    amplitudeRef.current = 0
    speakingRef.current  = false
    setPhase('idle')
  }, [])

  // ── Tool runner ─────────────────────────────────────────────────────────────
  const runTool = useCallback(async (tool, instruction = '') => {
    if (!meetingId || toolRunning.current) return
    toolRunning.current = true
    try {
      setActiveTool(tool)
      setUsedTools(prev => prev.includes(tool) ? prev : [...prev, tool])
      setToolData(prev => ({ ...prev, [tool]: { status: 'loading', content: null } }))

      const endpoint = ENDPOINTS[tool] || `/tools/${tool}`
      const res = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          meeting_id:    meetingId,
          transcript_id: meetingId,
          instruction:   instruction,
        }),
      })
      if (!res.ok) throw new Error(`API Error (${res.status})`)
      const data    = await res.json()
      const content = tool === 'get_transcript' ? (data.transcript || data) : data
      setToolData(prev => ({ ...prev, [tool]: { status: 'done', content } }))
    } catch (err) {
      console.error('[Tool failed]:', err)
      setToolData(prev => ({ ...prev, [tool]: { status: 'error', content: null } }))
      await speakText("I ran into an issue with that. Please try again.")
    } finally {
      toolRunning.current = false
    }
  }, [meetingId, speakText])

  // ── Recording ───────────────────────────────────────────────────────────────
  const startRecording = useCallback(async () => {
    if (phaseRef.current !== 'idle') return
    setError('')
    let stream
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }) }
    catch { setError('Microphone access denied.'); return }

    chunksRef.current = []
    const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    mediaRef.current = recorder
    setRecording(true)
    setPhase('listening')

    try {
      if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') audioCtxRef.current = new AudioContext()
      if (audioCtxRef.current.state === 'suspended') audioCtxRef.current.resume()
      const ctx = audioCtxRef.current
      const src = ctx.createMediaStreamSource(stream)
      const an  = ctx.createAnalyser()
      an.fftSize = 256; src.connect(an)
      const data = new Uint8Array(an.frequencyBinCount)
      const read = () => {
        if (!mediaRef.current) return
        an.getByteFrequencyData(data)
        amplitudeRef.current = Math.min(data.reduce((a, b) => a + b, 0) / data.length / 80, 1)
        requestAnimationFrame(read)
      }
      read()
    } catch {}

    recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
    recorder.start(100)
  }, [])

  const stopRecording = useCallback(async () => {
    const recorder = mediaRef.current
    if (!recorder) return
    setRecording(false)
    setPhase('thinking')
    amplitudeRef.current = 0.2

    recorder.onstop = async () => {
      recorder.stream?.getTracks().forEach(t => t.stop())
      mediaRef.current = null
      const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
      chunksRef.current = []
      if (blob.size < 100) { setPhase('idle'); amplitudeRef.current = 0; return }

      try {
        const form = new FormData()
        form.append('file', blob, 'recording.webm')
        const sttRes = await fetch(`${API}/stt`, { method: 'POST', body: form })
        if (!sttRes.ok) throw new Error(`STT error: ${sttRes.status}`)
        const { text } = await sttRes.json()
        if (!text?.trim()) { setPhase('idle'); amplitudeRef.current = 0; return }

        const userText = text.trim()
        setCaption(userText)
        if (!meetingId) throw new Error('No meetingId')

        const nioRes = await fetch(`${API}/nio/ask`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            meeting_id: meetingId,
            question:   userText,
            history:    historyRef.current.slice(-10),
          }),
        })
        if (!nioRes.ok) throw new Error(`Nio error: ${nioRes.status}`)
        const nioData = await nioRes.json()

        // ── Tool detection ──────────────────────────────────────────────────
        let detectedTool = nioData.tool
        if (!detectedTool && typeof nioData.answer === 'string') {
          try {
            const parsed = JSON.parse(nioData.answer.trim())
            if (parsed?.tool) detectedTool = parsed.tool
          } catch {}
        }

        if (detectedTool) {
          const toolAnswer = nioData.answer?.trim()
          // Only speak if toolAnswer is legitimate conversational text, NEVER if it's the raw tool JSON
          const isRawJson = toolAnswer?.startsWith('{') && toolAnswer?.includes('tool')
          if (toolAnswer && !isRawJson) {
            setCaption(toolAnswer)
            await speakText(toolAnswer)
            setCaption('')
          }

          if (nioData.background_tool?.name === 'send_email') {
            const params = nioData.background_tool.params || {}
            fetch(`${API}/tools/send-email`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                meeting_id:        meetingId,
                include_summary:   params.include_summary   ?? true,
                include_tasks:     params.include_tasks     ?? true,
                include_decisions: params.include_decisions ?? false,
              }),
            }).catch(e => console.warn('[bg email]:', e))
          }

          setPhase('idle')
          amplitudeRef.current = 0
          await runTool(detectedTool, userText)
          return
        }

        // ── Background email only ───────────────────────────────────────────
        if (nioData.background_tool?.name === 'send_email') {
          const params = nioData.background_tool.params || {}
          fetch(`${API}/tools/send-email`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              meeting_id:        meetingId,
              include_summary:   params.include_summary   ?? true,
              include_tasks:     params.include_tasks     ?? true,
              include_decisions: params.include_decisions ?? false,
            }),
          }).catch(e => console.warn('[bg email]:', e))
        }

        // ── Normal conversational response ──────────────────────────────────
        const answer = nioData.answer
        if (!answer?.trim()) throw new Error('Empty response')
        historyRef.current.push({ role: 'user',      content: userText })
        historyRef.current.push({ role: 'assistant', content: answer   })
        setCaption(answer)
        await speakText(answer)
        setCaption('')

      } catch (e) {
        setError(e.message || 'Something went wrong.')
        setCaption('')
        setPhase('idle')
        amplitudeRef.current = 0
      }
    }
    recorder.stop()
  }, [meetingId, speakText, runTool])

  // ── Theme ────────────────────────────────────────────────────────────────────
  const th = dark ? {
    bg: '#000000',
    bgGlow: 'radial-gradient(circle, #1a0050 0%, transparent 70%)',
    wordmark: 'rgba(255,255,255,0.35)',
    phaseColor: 'rgba(255,255,255,0.4)',
    captionCol: 'rgba(255,255,255,0.75)',
    endBg: 'rgba(255,40,40,0.15)', endBorder: 'rgba(255,60,60,0.3)',
    micBg:     (r) => r ? 'rgba(0,100,255,0.35)'         : 'rgba(255,255,255,0.08)',
    micBorder: (r) => r ? 'rgba(0,150,255,0.7)'          : 'rgba(255,255,255,0.15)',
    micShadow: (r) => r ? '0 0 24px rgba(0,100,255,0.4)' : 'none',
    micIcon:   (r) => r ? '#4499ff'                       : 'rgba(255,255,255,0.6)',
    volBg: 'rgba(255,255,255,0.06)', volBorder: 'rgba(255,255,255,0.1)', volIcon: 'rgba(255,255,255,0.4)',
    toggleBg: 'rgba(255,255,255,0.1)', toggleBorder: 'rgba(255,255,255,0.15)', toggleIcon: 'rgba(255,255,255,0.5)',
    tabBg: 'rgba(255,255,255,0.04)', tabBorder: 'rgba(255,255,255,0.08)', tabActive: 'rgba(99,102,241,0.25)',
  } : {
    bg: '#f0f4ff',
    bgGlow: 'radial-gradient(circle, rgba(26,115,232,0.10) 0%, transparent 70%)',
    wordmark: 'rgba(26,26,46,0.4)',
    phaseColor: '#9aa0a6',
    captionCol: '#1a1a2e',
    endBg: 'rgba(255,40,40,0.08)', endBorder: 'rgba(255,60,60,0.2)',
    micBg:     (r) => r ? 'rgba(26,115,232,0.15)'          : 'rgba(255,255,255,0.9)',
    micBorder: (r) => r ? 'rgba(26,115,232,0.6)'           : 'rgba(26,115,232,0.25)',
    micShadow: (r) => r ? '0 0 24px rgba(26,115,232,0.25)' : '0 2px 12px rgba(26,115,232,0.12)',
    micIcon:   (r) => r ? '#1a73e8'                        : '#5f6368',
    volBg: 'rgba(255,255,255,0.9)', volBorder: 'rgba(26,115,232,0.15)', volIcon: '#9aa0a6',
    toggleBg: 'rgba(255,255,255,0.7)', toggleBorder: 'rgba(26,115,232,0.15)', toggleIcon: '#5f6368',
    tabBg: 'rgba(255,255,255,0.7)', tabBorder: 'rgba(99,102,241,0.12)', tabActive: 'rgba(99,102,241,0.12)',
  }

  const phaseLabel  = { idle: 'Hold to speak', listening: 'Listening...', thinking: 'Thinking...', speaking: 'Nio' }[phase] || 'Hold to speak'
  const accentColor = dark ? 'rgba(99,102,241,0.9)' : '#6366f1'
  const SPHERE_SIZE = 300, CTRL_BOTTOM = 52, MIC_SIZE = 72
  const SPHERE_BOTTOM = CTRL_BOTTOM + MIC_SIZE + 32

  return (
    <div style={{
      minHeight: '100vh', background: th.bg,
      display: 'flex', alignItems: 'stretch',
      fontFamily: "'Google Sans', system-ui, sans-serif",
      position: 'relative', overflow: 'hidden',
      transition: 'background 0.3s',
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600&display=swap');
        * { box-sizing: border-box; }
        .panel-scroll::-webkit-scrollbar { width: 3px; }
        .panel-scroll::-webkit-scrollbar-track { background: transparent; }
        .panel-scroll::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.25); border-radius: 4px; }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
      `}</style>

      {/* Background glow */}
      <div ref={bgRef} style={{
        position: 'absolute', width: 420, height: 420, borderRadius: '50%',
        background: th.bgGlow, opacity: 0.4, pointerEvents: 'none', filter: 'blur(70px)',
        left: activeAxis, top: '50%',
        transform: 'translateY(-50%) translateX(-50%)',
        transition: 'left 0.55s cubic-bezier(0.34,1.56,0.64,1)',
      }} />

      {/* Top bar */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, zIndex: 10,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '24px 24px 0',
      }}>
        <span style={{ fontSize: 16, fontWeight: 600, color: th.wordmark, letterSpacing: '0.08em' }}>meetcore</span>
        <span style={{
          position: 'absolute', right: 120,
          fontSize: 11, color: th.phaseColor,
          letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 500,
        }}>{phaseLabel}</span>
        <button onClick={() => setSettingsOpen(true)} style={{
          position: 'absolute', right: 68, top: 18,
          width: 36, height: 36, borderRadius: '50%',
          background: th.toggleBg, border: `1px solid ${th.toggleBorder}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', transition: 'all 0.2s',
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" stroke={th.toggleIcon} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" stroke={th.toggleIcon} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <button onClick={() => setDark(d => !d)} style={{
          position: 'absolute', right: 20, top: 18,
          width: 36, height: 36, borderRadius: '50%',
          background: th.toggleBg, border: `1px solid ${th.toggleBorder}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', transition: 'all 0.2s',
        }}>
          {dark
            ? <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="4" stroke={th.toggleIcon} strokeWidth="1.8"/>
                <path d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M2 12h2M20 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
                  stroke={th.toggleIcon} strokeWidth="1.8" strokeLinecap="round"/>
              </svg>
            : <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z"
                  stroke={th.toggleIcon} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
          }
        </button>
      </div>

      {/* Tool Panel — adaptive size */}
      <div style={{
        position: 'absolute',
        top: '50%', transform: 'translateY(-50%)',
        left: panelOpen ? 52 : -500,
        transition: 'left 0.55s cubic-bezier(0.34,1.56,0.64,1)',
        zIndex: 5,
      }}>
        {panelOpen && (
          <PanelShell dark={dark}>
            {activeTool === 'get_transcript'    && toolData.get_transcript.content    &&
              <TranscriptPanel  content={toolData.get_transcript.content}   dark={dark}
                onComplete={() => speakText("There you go, the full transcript is up.")} />}
            {activeTool === 'summarize_meeting' && toolData.summarize_meeting.content &&
              <SummaryPanel     content={toolData.summarize_meeting.content} dark={dark}
                onComplete={() => speakText("Here's the summary. Let me know if you need anything else.")} />}
            {activeTool === 'action_items'      && toolData.action_items.content      &&
              <ActionItemsPanel content={toolData.action_items.content}      dark={dark}
                onComplete={() => speakText("Those are all the action items from the meeting.")} />}
            {activeTool === 'draft_email'       && toolData.draft_email.content       &&
              <DraftEmailPanel  content={toolData.draft_email.content}       dark={dark}
                onComplete={() => speakText("Done. The email draft is ready for you.")} />}
            {activeTool === 'schedule_meeting'  && toolData.schedule_meeting.content  &&
              <CalendarPanel    content={toolData.schedule_meeting.content}  dark={dark}
                onComplete={() => speakText("I've drafted the calendar invite for you.")} />}
            {activeTool && !toolData[activeTool]?.content && (
              <div style={{ padding: 32, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <p style={{ fontSize: 13, color: dark ? 'rgba(255,255,255,0.3)' : '#9aa0a6', margin: 0 }}>
                  {toolData[activeTool]?.status === 'error' ? 'Something went wrong.' : 'Working on it...'}
                </p>
              </div>
            )}
          </PanelShell>
        )}
      </div>

      {/* Settings Modal */}
      {settingsOpen && <SettingsModal dark={dark} onClose={() => setSettingsOpen(false)} />}

      {/* Tab strip */}
      {usedTools.length > 0 && (
        <div style={{
          position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)',
          display: 'flex', flexDirection: 'column', gap: 6,
          padding: '10px 6px',
          background: th.tabBg, border: `1px solid ${th.tabBorder}`,
          borderLeft: 'none', borderRadius: '0 10px 10px 0',
          backdropFilter: 'blur(12px)', zIndex: 10,
        }}>
          {usedTools.map(tool => (
            <button key={tool}
              onClick={() => setActiveTool(activeTool === tool ? null : tool)}
              title={tool.replace(/_/g, ' ')}
              style={{
                width: 38, height: 38, borderRadius: 8,
                background: activeTool === tool ? th.tabActive : 'transparent',
                border: `1px solid ${activeTool === tool ? accentColor : 'transparent'}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', transition: 'all 0.15s',
              }}
            >
              {TOOL_ICONS[tool]?.(activeTool === tool ? accentColor : (dark ? 'rgba(255,255,255,0.4)' : '#9aa0a6'))}
            </button>
          ))}
        </div>
      )}

      {/* Sphere */}
      <div style={{
        position: 'absolute', bottom: SPHERE_BOTTOM,
        left: activeAxis, transform: 'translateX(-50%)',
        width: SPHERE_SIZE, height: SPHERE_SIZE,
        transition: 'left 0.55s cubic-bezier(0.34,1.56,0.64,1)',
      }}>
        <FluidSphere canvasRef={canvasRef} amplitudeRef={amplitudeRef} sloshRef={sloshRef} dark={dark} />
      </div>

      {/* Caption */}
      {(caption || error) && (
        <div className="no-scrollbar" style={{
          position: 'absolute', top: 72,
          bottom: SPHERE_BOTTOM + SPHERE_SIZE + 12,
          left: activeAxis, transform: 'translateX(-50%)',
          transition: 'left 0.55s cubic-bezier(0.34,1.56,0.64,1)',
          width: 'min(640px, 85vw)',
          overflowY: 'auto',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '8px 20px', zIndex: 8,
        }}>
          <p style={{
            fontSize: 15, lineHeight: 1.7,
            color: error ? '#d93025' : th.captionCol,
            margin: 'auto 0', textAlign: 'center', wordBreak: 'break-word',
          }}>
            {error || caption}
          </p>
        </div>
      )}

      {/* Controls */}
      <div style={{
        position: 'absolute', bottom: CTRL_BOTTOM,
        left: activeAxis, transform: 'translateX(-50%)',
        transition: 'left 0.55s cubic-bezier(0.34,1.56,0.64,1)',
        display: 'flex', alignItems: 'center', gap: 48,
      }}>
        <button onClick={onEnd} style={{
          width: 52, height: 52, borderRadius: '50%',
          background: th.endBg, border: `1px solid ${th.endBorder}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', transition: 'all 0.2s',
        }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.9 9.5a19.79 19.79 0 01-3.07-8.68A2 2 0 012.81 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.91 9.91a16 16 0 006.18 6.18l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z" fill="#ff4444"/>
            <line x1="23" y1="1" x2="1" y2="23" stroke="#ff4444" strokeWidth="2.2" strokeLinecap="round"/>
          </svg>
        </button>

        <button
          onPointerDown={startRecording}
          onPointerUp={stopRecording}
          disabled={phase === 'thinking' || phase === 'speaking'}
          style={{
            width: MIC_SIZE, height: MIC_SIZE, borderRadius: '50%',
            background: th.micBg(recording),
            border: `1.5px solid ${th.micBorder(recording)}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: phase === 'thinking' || phase === 'speaking' ? 'not-allowed' : 'pointer',
            boxShadow: th.micShadow(recording),
            transition: 'all 0.2s', touchAction: 'none', userSelect: 'none',
          }}
        >
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
            <rect x="9" y="2" width="6" height="11" rx="3" fill={th.micIcon(recording)} />
            <path d="M5 10a7 7 0 0014 0" stroke={th.micIcon(recording)} strokeWidth="1.8" strokeLinecap="round"/>
            <path d="M12 19v3"           stroke={th.micIcon(recording)} strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
        </button>

        <button style={{
          width: 52, height: 52, borderRadius: '50%',
          background: th.volBg, border: `1px solid ${th.volBorder}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', transition: 'all 0.2s',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M11 5L6 9H2v6h4l5 4V5z"
              stroke={th.volIcon} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07"
              stroke={th.volIcon} strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
        </button>
      </div>
    </div>
  )
}
