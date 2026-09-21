// src/pages/MainScreen.jsx
import { useState, useRef, useCallback, useEffect } from 'react'
import { uploadMeeting, streamStatus, askNio } from '../lib/api'

const ALLOWED = ['.mp4', '.mp3', '.wav', '.m4a', '.mpeg', '.mpg']

const TOOLS = [
  { icon: '✦', label: 'Task extractor',   desc: 'Every action item and owner' },
  { icon: '◈', label: 'Deadline tracker', desc: 'Specific and vague dates resolved' },
  { icon: '◉', label: 'Decision log',     desc: 'What was agreed and by whom' },
  { icon: '◇', label: 'Priority brief',   desc: 'Three things to act on now' },
]

const NARRATION = {
  transcribing: (msg) => msg?.includes('elapsed')
    ? `Still transcribing — ${msg.match(/\((.+)\)/)?.[1] || ''} in.`
    : 'Reading through the audio now...',
  transcribed:  () => 'Got the full transcript. Going through what happened.',
  tasks:        () => 'Pulling out every action item and who owns it.',
  deadlines:    () => 'Checking for dates — firm ones and the vague kind.',
  decisions:    () => 'Logging what was actually decided, not just discussed.',
  brief:        () => 'Figuring out the three things to move on now.',
  saving:       () => 'Writing everything to memory.',
  embedding:    () => 'Building my knowledge of this meeting. Almost there.',
  ready:        () => null, // handled separately
  failed:       (msg) => `Something went wrong: ${msg}`,
}

function Clock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  const date = now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
  const time = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  return (
    <div style={{ position: 'fixed', bottom: 24, left: 24, zIndex: 20, pointerEvents: 'none' }}>
      <p style={{ margin: 0, fontSize: 11, color: '#9aa0a6' }}>{date}</p>
      <p style={{ margin: 0, fontSize: 18, fontWeight: 500, color: '#3c4043', letterSpacing: '-0.5px', lineHeight: 1.2 }}>{time}</p>
    </div>
  )
}

function ArcBackground() {
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 0, overflow: 'hidden', pointerEvents: 'none' }}>
      <svg width="100%" height="100%" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice"
        style={{ position: 'absolute', inset: 0 }}>
        <style>{`
          @keyframes arcSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
          .ag1 { transform-origin: 820px 500px; animation: arcSpin 28s linear infinite; }
          .ag2 { transform-origin: 820px 500px; animation: arcSpin 40s linear infinite reverse; }
        `}</style>
        <g className="ag1">
          {[180,220,260,300,340,380,420,460,500,540].map((r,i) => (
            <circle key={i} cx="820" cy="500" r={r} fill="none"
              stroke={`rgba(26,115,232,${0.04+i*0.008})`} strokeWidth="1"
              strokeDasharray={`${r*0.9} ${r*5.37}`}/>
          ))}
        </g>
        <g className="ag2">
          {[200,250,300,350,400,450].map((r,i) => (
            <circle key={i} cx="820" cy="500" r={r} fill="none"
              stroke={`rgba(26,115,232,${0.03+i*0.005})`} strokeWidth="0.8"
              strokeDasharray={`${r*0.6} ${r*5.8}`} strokeDashoffset={r*1.2}/>
          ))}
        </g>
      </svg>
    </div>
  )
}

// Message types: { id, role: 'user'|'nio', type: 'file'|'log'|'text', ... }
export default function MainScreen() {
  const [messages, setMessages]     = useState([
    { id: 0, role: 'nio', type: 'text', text: "Hey — drop in a meeting recording and I'll go through it for you. You can start asking questions the moment I'm done." }
  ])
  const [input, setInput]           = useState('')
  const [meetingId, setMeetingId]   = useState(null)
  const [phase, setPhase]           = useState('idle') // idle | uploading | processing | ready
  const [logLines, setLogLines]     = useState([])
  const [toolsState, setToolsState] = useState('grid') // grid | list | hidden
  const [chatLoading, setChatLoading] = useState(false)
  const [history, setHistory]       = useState([])

  const fileRef   = useRef(null)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, logLines, chatLoading])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }, [input])

  const addMessage = useCallback((msg) => {
    setMessages(prev => [...prev, { id: Date.now() + Math.random(), ...msg }])
  }, [])

  const processFile = useCallback(async (f) => {
    const ext = '.' + f.name.split('.').pop().toLowerCase()
    if (!ALLOWED.includes(ext)) {
      addMessage({ role: 'nio', type: 'text', text: `Can't read that format. Drop in an MP4, MP3, WAV, M4A, or MPEG file.` })
      return
    }

    // User file bubble
    addMessage({
      role: 'user', type: 'file',
      fileName: f.name,
      fileSize: (f.size / 1024 / 1024).toFixed(1) + ' MB',
    })

    setPhase('uploading')
    setLogLines([])
    setToolsState('list') // morph tools to right sidebar

    let mid
    try {
      const res = await uploadMeeting(f)
      mid = res.meeting_id
      setMeetingId(mid)
    } catch (e) {
      addMessage({ role: 'nio', type: 'text', text: `Upload failed — ${e.message}` })
      setPhase('idle')
      setToolsState('grid')
      return
    }

    setPhase('processing')

    streamStatus(
      mid,
      (event) => {
        if (event.step === 'ready') return
        const narrate = NARRATION[event.step]
        if (narrate) {
          const text = narrate(event.message || '')
          if (text) setLogLines(prev => [...prev, { id: Date.now() + Math.random(), text }])
        }
      },
      () => {
        setPhase('ready')
        setTimeout(() => setToolsState('hidden'), 800) // auto-minimize
        addMessage({
          role: 'nio', type: 'text',
          text: "Done. I've gone through the whole thing — tasks, deadlines, decisions, the works. What do you want to know?"
        })
      },
      () => {
        addMessage({ role: 'nio', type: 'text', text: "Lost connection during processing. Try again." })
        setPhase('idle')
        setToolsState('grid')
      }
    )
  }, [addMessage])

  const sendMessage = useCallback(async () => {
    const text = input.trim()
    if (!text || chatLoading || phase !== 'ready') return

    addMessage({ role: 'user', type: 'text', text })
    setInput('')
    setChatLoading(true)

    const newHistory = [...history, { role: 'user', content: text }]

    try {
      const res = await askNio(meetingId, text, history)
      const answer = res.answer
      addMessage({ role: 'nio', type: 'text', text: answer })
      setHistory([...newHistory, { role: 'assistant', content: answer }])
    } catch {
      addMessage({ role: 'nio', type: 'text', text: "Something went wrong. Try again." })
    } finally {
      setChatLoading(false)
    }
  }, [input, chatLoading, phase, meetingId, history, addMessage])

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const onDrop = (e) => {
    e.preventDefault()
    const f = e.dataTransfer.files?.[0]
    if (f) processFile(f)
  }

  const canChat = phase === 'ready' && !chatLoading

  return (
    <div
      style={{ minHeight: '100vh', background: '#f0f4ff', display: 'flex', flexDirection: 'column', fontFamily: "'Google Sans', system-ui, sans-serif", position: 'relative' }}
      onDragOver={e => e.preventDefault()}
      onDrop={onDrop}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600&display=swap');
        * { box-sizing: border-box; }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 0%,80%,100% { opacity:.25; transform:scale(.8); } 40% { opacity:1; transform:scale(1); } }
        @keyframes slideInRight { from { opacity:0; transform:translateX(20px); } to { opacity:1; transform:translateX(0); } }
      `}</style>

      <ArcBackground />

      {/* Nav */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 30,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 28px',
        background: 'rgba(240,244,255,0.88)',
        backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(26,115,232,0.08)',
      }}>
        <span style={{ fontSize: 17, fontWeight: 600, color: '#1a1a2e', letterSpacing: '-0.3px' }}>meetcore</span>
        <button style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M3 5h14M3 10h14M3 15h14" stroke="#5f6368" strokeWidth="1.4" strokeLinecap="round"/>
          </svg>
        </button>
      </nav>

      {/* Main area */}
      <div style={{ flex: 1, display: 'flex', paddingTop: 64, paddingBottom: 160 }}>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '32px 0' }}>
          <div style={{ maxWidth: 680, margin: '0 auto', padding: '0 24px', display: 'flex', flexDirection: 'column', gap: 20 }}>

            {messages.map(msg => {
              if (msg.role === 'user' && msg.type === 'file') {
                return (
                  <div key={msg.id} style={{ display: 'flex', justifyContent: 'flex-end', animation: 'fadeUp 0.2s ease' }}>
                    <div style={{
                      background: 'rgba(255,255,255,0.82)',
                      backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
                      border: '1px solid rgba(26,115,232,0.15)',
                      borderRadius: '14px 14px 4px 14px',
                      padding: '12px 16px',
                      display: 'flex', alignItems: 'center', gap: 12,
                    }}>
                      <div style={{ width: 36, height: 36, borderRadius: 10, background: '#e8f0fe', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                          <path d="M9 18V6l12-3v13" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                          <circle cx="6" cy="18" r="3" stroke="#1a73e8" strokeWidth="1.8"/>
                          <circle cx="18" cy="15" r="3" stroke="#1a73e8" strokeWidth="1.8"/>
                        </svg>
                      </div>
                      <div>
                        <p style={{ margin: 0, fontSize: 13, fontWeight: 500, color: '#1a1a2e' }}>{msg.fileName}</p>
                        <p style={{ margin: 0, fontSize: 11, color: '#9aa0a6' }}>{msg.fileSize}</p>
                      </div>
                    </div>
                  </div>
                )
              }

              if (msg.role === 'user' && msg.type === 'text') {
                return (
                  <div key={msg.id} style={{ display: 'flex', justifyContent: 'flex-end', animation: 'fadeUp 0.2s ease' }}>
                    <div style={{
                      maxWidth: '72%',
                      background: 'rgba(255,255,255,0.82)',
                      backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
                      border: '1px solid rgba(26,115,232,0.12)',
                      borderRadius: '14px 14px 4px 14px',
                      padding: '10px 14px',
                      fontSize: 14, color: '#1a1a2e', lineHeight: 1.6,
                    }}>
                      {msg.text}
                    </div>
                  </div>
                )
              }

              // Nio text message
              return (
                <div key={msg.id} style={{ display: 'flex', flexDirection: 'column', gap: 6, animation: 'fadeUp 0.2s ease' }}>
                  <span style={{ fontSize: 11, color: '#9aa0a6', fontWeight: 500, letterSpacing: '0.06em', textTransform: 'uppercase' }}>Nio</span>
                  <p style={{ margin: 0, fontSize: 14, color: '#1a1a2e', lineHeight: 1.65, maxWidth: '80%' }}>{msg.text}</p>
                </div>
              )
            })}

            {/* Streaming log — shown as a Nio bubble while processing */}
            {logLines.length > 0 && phase === 'processing' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, animation: 'fadeUp 0.2s ease' }}>
                <span style={{ fontSize: 11, color: '#9aa0a6', fontWeight: 500, letterSpacing: '0.06em', textTransform: 'uppercase' }}>Nio</span>
                <div style={{
                  background: 'rgba(255,255,255,0.72)',
                  backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
                  border: '1px solid rgba(26,115,232,0.1)',
                  borderRadius: '4px 14px 14px 14px',
                  padding: '14px 16px',
                  maxWidth: '82%',
                  borderLeft: '2px solid rgba(26,115,232,0.25)',
                }}>
                  {logLines.map((line, i) => {
                    const isLast = i === logLines.length - 1
                    return (
                      <div key={line.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: i < logLines.length - 1 ? 8 : 0 }}>
                        <div style={{
                          width: 6, height: 6, borderRadius: '50%', flexShrink: 0, marginTop: 5,
                          background: isLast ? 'transparent' : '#1a73e8',
                          border: isLast ? '1.5px solid #1a73e8' : 'none',
                        }} />
                        <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: isLast ? '#1a1a2e' : '#9aa0a6', fontWeight: isLast ? 500 : 400 }}>
                          {line.text}
                        </p>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {chatLoading && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <span style={{ fontSize: 11, color: '#9aa0a6', fontWeight: 500, letterSpacing: '0.06em', textTransform: 'uppercase' }}>Nio</span>
                <div style={{ display: 'flex', gap: 5, alignItems: 'center', height: 22 }}>
                  {[0,1,2].map(i => (
                    <div key={i} style={{ width: 6, height: 6, borderRadius: '50%', background: '#1a73e8', animation: `pulse 1.2s ease-in-out ${i*0.18}s infinite` }} />
                  ))}
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* Tools panel — right sidebar when list/hidden */}
        {toolsState === 'list' && (
          <div style={{
            width: 220, flexShrink: 0,
            background: 'rgba(255,255,255,0.65)',
            backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
            borderLeft: '1px solid rgba(26,115,232,0.1)',
            padding: '80px 16px 24px',
            display: 'flex', flexDirection: 'column', gap: 12,
            animation: 'slideInRight 0.25s ease',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 11, color: '#9aa0a6', letterSpacing: '0.05em' }}>Tools running</span>
              <button
                onClick={() => setToolsState('hidden')}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: '#9aa0a6' }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                </svg>
              </button>
            </div>
            {TOOLS.map((t, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '8px 10px', borderRadius: 10, background: 'rgba(232,240,254,0.5)' }}>
                <span style={{ fontSize: 13, color: '#1a73e8', flexShrink: 0 }}>{t.icon}</span>
                <div>
                  <p style={{ margin: 0, fontSize: 12, fontWeight: 500, color: '#1a1a2e' }}>{t.label}</p>
                  <p style={{ margin: 0, fontSize: 11, color: '#9aa0a6' }}>{t.desc}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Bottom — input + tools grid */}
      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 20,
        background: 'rgba(240,244,255,0.92)',
        backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
        borderTop: '1px solid rgba(26,115,232,0.08)',
        padding: '14px 24px 20px',
      }}>
        <div style={{ maxWidth: 680, margin: '0 auto' }}>

          {/* Tools grid — only when idle */}
          {toolsState === 'grid' && (
            <div style={{
              background: 'rgba(255,255,255,0.6)',
              backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
              border: '1px solid rgba(26,115,232,0.1)',
              borderRadius: 14,
              padding: '16px 20px',
              marginBottom: 12,
            }}>
              <p style={{ fontSize: 11, color: '#9aa0a6', margin: '0 0 12px', letterSpacing: '0.04em' }}>Available tools</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px 32px' }}>
                {TOOLS.map((t, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                    <span style={{ fontSize: 14, color: '#1a73e8', flexShrink: 0, marginTop: 1 }}>{t.icon}</span>
                    <div>
                      <p style={{ margin: '0 0 1px', fontSize: 12, fontWeight: 500, color: '#1a1a2e' }}>{t.label}</p>
                      <p style={{ margin: 0, fontSize: 11, color: '#9aa0a6' }}>{t.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid rgba(26,115,232,0.07)', display: 'flex', justifyContent: 'flex-end' }}>
                <button style={{
                  fontSize: 12, color: '#1a73e8', background: 'none',
                  border: '1px solid rgba(26,115,232,0.25)', borderRadius: 20,
                  padding: '5px 14px', cursor: 'pointer', fontFamily: 'inherit',
                }}>
                  Create tool
                </button>
              </div>
            </div>
          )}

          {/* Input row */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>

            {/* Upload button */}
            <button
              onClick={() => fileRef.current?.click()}
              disabled={phase === 'uploading' || phase === 'processing'}
              title="Upload recording"
              style={{
                width: 42, height: 42, borderRadius: 12, flexShrink: 0,
                background: 'rgba(255,255,255,0.8)',
                border: '1px solid rgba(26,115,232,0.2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: phase === 'idle' || phase === 'ready' ? 'pointer' : 'not-allowed',
                opacity: phase === 'uploading' || phase === 'processing' ? 0.4 : 1,
                transition: 'all 0.15s',
              }}
            >
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66L9.41 17.41a2 2 0 01-2.83-2.83l8.49-8.48" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>

            <input ref={fileRef} type="file" accept={ALLOWED.join(',')} style={{ display: 'none' }}
              onChange={e => { const f = e.target.files?.[0]; if (f) processFile(f) }} />

            {/* Text input */}
            <div style={{
              flex: 1,
              background: 'rgba(255,255,255,0.85)',
              border: '1px solid rgba(26,115,232,0.18)',
              borderRadius: 12,
              display: 'flex', alignItems: 'flex-end',
              transition: 'border-color 0.15s',
            }}
              onFocusCapture={e => e.currentTarget.style.borderColor = '#1a73e8'}
              onBlurCapture={e => e.currentTarget.style.borderColor = 'rgba(26,115,232,0.18)'}
            >
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={onKey}
                placeholder={phase === 'ready' ? "Ask Nio anything about the meeting..." : "Upload a recording to get started..."}
                disabled={!canChat}
                rows={1}
                style={{
                  flex: 1, resize: 'none', border: 'none', outline: 'none',
                  padding: '11px 14px', fontSize: 14, color: '#1a1a2e',
                  lineHeight: 1.55, background: 'transparent',
                  maxHeight: 120, overflowY: 'auto', fontFamily: 'inherit',
                  opacity: canChat ? 1 : 0.5,
                }}
              />
            </div>

            {/* Send */}
            <button
              onClick={sendMessage}
              disabled={!canChat || !input.trim()}
              style={{
                width: 42, height: 42, borderRadius: 12, flexShrink: 0,
                background: canChat && input.trim() ? '#1a73e8' : '#e8eaed',
                border: 'none', cursor: canChat && input.trim() ? 'pointer' : 'default',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'background 0.15s',
              }}
            >
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M13 6l6 6-6 6" stroke={canChat && input.trim() ? '#fff' : '#bdc1c6'} strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <Clock />
    </div>
  )
}