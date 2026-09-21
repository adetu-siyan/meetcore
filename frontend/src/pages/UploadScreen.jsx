// // src/pages/UploadScreen.jsx
// import { useState, useRef, useCallback, useEffect } from 'react'
// import { uploadMeeting, streamStatus } from '../lib/api'

// const ALLOWED = ['.mp4', '.mp3', '.wav', '.m4a', '.mpeg', '.mpg']

// const TOOLS = [
//   { icon: '✦', label: 'Task extractor',   desc: 'Every action item and owner' },
//   { icon: '◈', label: 'Deadline tracker', desc: 'Specific and vague dates resolved' },
//   { icon: '◉', label: 'Decision log',     desc: 'What was agreed and by whom' },
//   { icon: '◇', label: 'Priority brief',   desc: 'Three things to act on now' },
// ]

// const NARRATION = {
//   transcribing: (msg) => msg?.includes('elapsed')
//     ? `Still transcribing — ${msg.match(/\((.+)\)/)?.[1] || ''} in.`
//     : 'Reading through the audio now...',
//   transcribed:  () => 'Got the full transcript. Going through what happened.',
//   tasks:        () => 'Pulling out every action item and who owns it.',
//   deadlines:    () => 'Checking for dates — firm ones and the vague kind.',
//   decisions:    () => 'Logging what was actually decided, not just discussed.',
//   brief:        () => 'Figuring out the three things you need to move on now.',
//   saving:       () => 'Writing everything to memory.',
//   embedding:    () => 'Building my knowledge of this meeting. Almost there.',
//   ready:        () => "Done. Ask me anything.",
//   failed:       (msg) => `Something went wrong: ${msg}`,
// }

// function Clock() {
//   const [now, setNow] = useState(new Date())
//   useEffect(() => {
//     const t = setInterval(() => setNow(new Date()), 1000)
//     return () => clearInterval(t)
//   }, [])
//   const date = now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
//   const time = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
//   return (
//     <div style={{ position: 'fixed', bottom: 24, left: 24, zIndex: 20 }}>
//       <p style={{ margin: 0, fontSize: 11, color: '#9aa0a6', letterSpacing: '0.04em' }}>{date}</p>
//       <p style={{ margin: 0, fontSize: 18, fontWeight: 500, color: '#3c4043', letterSpacing: '-0.5px', lineHeight: 1.2 }}>{time}</p>
//     </div>
//   )
// }

// function ArcBackground() {
//   return (
//     <div style={{
//       position: 'fixed', inset: 0, zIndex: 0,
//       overflow: 'hidden', pointerEvents: 'none',
//     }}>
//       <svg
//         width="100%" height="100%"
//         viewBox="0 0 1000 1000"
//         preserveAspectRatio="xMidYMid slice"
//         xmlns="http://www.w3.org/2000/svg"
//         style={{ position: 'absolute', inset: 0 }}
//       >
//         <style>{`
//           @keyframes arcSpin {
//             from { transform: rotate(0deg); }
//             to   { transform: rotate(360deg); }
//           }
//           .arc-group {
//             transform-origin: 820px 500px;
//             animation: arcSpin 28s linear infinite;
//           }
//           .arc-group-2 {
//             transform-origin: 820px 500px;
//             animation: arcSpin 40s linear infinite reverse;
//           }
//         `}</style>

//         <g className="arc-group">
//           {[180, 220, 260, 300, 340, 380, 420, 460, 500, 540].map((r, i) => (
//             <circle
//               key={i} cx="820" cy="500" r={r}
//               fill="none"
//               stroke={`rgba(26,115,232,${0.04 + i * 0.008})`}
//               strokeWidth="1"
//               strokeDasharray={`${r * 0.9} ${r * 5.37}`}
//               strokeDashoffset="0"
//             />
//           ))}
//         </g>

//         <g className="arc-group-2">
//           {[200, 250, 300, 350, 400, 450].map((r, i) => (
//             <circle
//               key={i} cx="820" cy="500" r={r}
//               fill="none"
//               stroke={`rgba(26,115,232,${0.03 + i * 0.005})`}
//               strokeWidth="0.8"
//               strokeDasharray={`${r * 0.6} ${r * 5.8}`}
//               strokeDashoffset={r * 1.2}
//             />
//           ))}
//         </g>
//       </svg>
//     </div>
//   )
// }

// export default function UploadScreen({ onReady, lastMeetingId }) {
//   const [phase, setPhase] = useState('idle')
//   const [lines, setLines] = useState([])
//   const [dragOver, setDragOver] = useState(false)
//   const [error, setError] = useState(null)
//   const [file, setFile] = useState(null)
//   const fileRef = useRef(null)

//   const addLine = useCallback((text) => {
//     setLines(prev => [...prev, { text, id: Date.now() + Math.random() }])
//   }, [])

//   const processFile = useCallback(async (f) => {
//     const ext = '.' + f.name.split('.').pop().toLowerCase()
//     if (!ALLOWED.includes(ext)) {
//       setError(`Unsupported format. Accepted: ${ALLOWED.join(' ')}`)
//       return
//     }
//     setError(null)
//     setFile(f)
//     setLines([])
//     setPhase('uploading')

//     let meetingId
//     try {
//       const res = await uploadMeeting(f)
//       meetingId = res.meeting_id
//     } catch (e) {
//       setError(e.message)
//       setPhase('idle')
//       return
//     }

//     setPhase('processing')
//     streamStatus(
//       meetingId,
//       (event) => {
//         const narrate = NARRATION[event.step]
//         if (narrate) addLine(narrate(event.message || ''))
//       },
//       () => { setPhase('done'); setTimeout(() => onReady(meetingId), 600) },
//       () => { setError('Lost connection.'); setPhase('idle') }
//     )
//   }, [onReady, addLine])

//   const onDrop = (e) => {
//     e.preventDefault(); setDragOver(false)
//     const f = e.dataTransfer.files?.[0]
//     if (f) processFile(f)
//   }

//   const isIdle = phase === 'idle'
//   const isProcessing = phase === 'processing' || phase === 'uploading'

//   return (
//     <div style={{
//       minHeight: '100vh',
//       background: '#f0f4ff',
//       fontFamily: "'Google Sans', system-ui, sans-serif",
//       position: 'relative',
//     }}>
//       <style>{`
//         @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600&display=swap');
//         * { box-sizing: border-box; }
//       `}</style>

//       <ArcBackground />

//       {/* Nav */}
//       <nav style={{
//         position: 'fixed', top: 0, left: 0, right: 0, zIndex: 20,
//         display: 'flex', alignItems: 'center', justifyContent: 'space-between',
//         padding: '18px 28px',
//         background: 'rgba(240,244,255,0.85)',
//         backdropFilter: 'blur(12px)',
//         WebkitBackdropFilter: 'blur(12px)',
//         borderBottom: '1px solid rgba(26,115,232,0.08)',
//       }}>
//         <span style={{ fontSize: 17, fontWeight: 600, color: '#1a1a2e', letterSpacing: '-0.3px' }}>meetcore</span>
//         <button style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}>
//           <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
//             <path d="M3 5h14M3 10h14M3 15h14" stroke="#5f6368" strokeWidth="1.4" strokeLinecap="round"/>
//           </svg>
//         </button>
//       </nav>

//       {/* Left sidebar */}
//       <div style={{
//         position: 'fixed', left: 24, top: '50%', transform: 'translateY(-50%)',
//         zIndex: 20, display: 'flex', flexDirection: 'column', gap: 12,
//       }}>
//         {/* Upload icon */}
//         <button
//           onClick={() => fileRef.current?.click()}
//           title="Upload recording"
//           style={{
//             width: 42, height: 42, borderRadius: 12,
//             background: 'rgba(255,255,255,0.8)',
//             backdropFilter: 'blur(8px)',
//             WebkitBackdropFilter: 'blur(8px)',
//             border: '1px solid rgba(26,115,232,0.15)',
//             display: 'flex', alignItems: 'center', justifyContent: 'center',
//             cursor: 'pointer', transition: 'all 0.15s',
//           }}
//           onMouseEnter={e => e.currentTarget.style.background = 'rgba(232,240,254,0.95)'}
//           onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.8)'}
//         >
//           <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
//             <path d="M12 15V5M12 5l-3.5 3.5M12 5l3.5 3.5" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
//             <path d="M20 17v1a2 2 0 01-2 2H6a2 2 0 01-2-2v-1" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round"/>
//           </svg>
//         </button>

//         {/* Nio icon */}
//         <button
//           onClick={() => lastMeetingId && onReady(lastMeetingId)}
//           title={lastMeetingId ? 'Back to Nio' : 'Upload a meeting first'}
//           style={{
//             width: 42, height: 42, borderRadius: 12,
//             background: lastMeetingId ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.4)',
//             backdropFilter: 'blur(8px)',
//             WebkitBackdropFilter: 'blur(8px)',
//             border: `1px solid ${lastMeetingId ? 'rgba(26,115,232,0.15)' : 'rgba(26,115,232,0.06)'}`,
//             display: 'flex', alignItems: 'center', justifyContent: 'center',
//             cursor: lastMeetingId ? 'pointer' : 'not-allowed',
//             transition: 'all 0.15s',
//             opacity: lastMeetingId ? 1 : 0.4,
//           }}
//           onMouseEnter={e => lastMeetingId && (e.currentTarget.style.background = 'rgba(232,240,254,0.95)')}
//           onMouseLeave={e => lastMeetingId && (e.currentTarget.style.background = 'rgba(255,255,255,0.8)')}
//         >
//           <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
//             <circle cx="12" cy="8" r="3.5" stroke={lastMeetingId ? '#1a73e8' : '#9aa0a6'} strokeWidth="1.8"/>
//             <path d="M5 19c0-3.314 3.134-6 7-6s7 2.686 7 6" stroke={lastMeetingId ? '#1a73e8' : '#9aa0a6'} strokeWidth="1.8" strokeLinecap="round"/>
//             <circle cx="18" cy="6" r="3" fill={lastMeetingId ? '#1a73e8' : '#9aa0a6'}/>
//             <path d="M17 6h2M18 5v2" stroke="white" strokeWidth="1.2" strokeLinecap="round"/>
//           </svg>
//         </button>
//       </div>

//       {/* Main content */}
//       <div style={{
//         minHeight: '100vh',
//         display: 'flex', flexDirection: 'column',
//         alignItems: 'center', justifyContent: 'center',
//         padding: '100px 80px 80px',
//         position: 'relative', zIndex: 10,
//       }}>

//         {isIdle && (
//           <div style={{ marginBottom: 28, textAlign: 'center' }}>
//             <h1 style={{ fontSize: 30, fontWeight: 500, color: '#1a1a2e', margin: '0 0 8px', letterSpacing: '-0.5px' }}>
//               Shall we tackle a session?
//             </h1>
//             <p style={{ fontSize: 15, color: '#5f6368', margin: 0 }}>
//               Drop in a recording — Nio will read it and be ready to answer anything.
//             </p>
//           </div>
//         )}

//         {/* Upload box */}
//         <div style={{ width: '100%', maxWidth: 560 }}>
//           <input ref={fileRef} type="file" accept={ALLOWED.join(',')} style={{ display: 'none' }}
//             onChange={e => { const f = e.target.files?.[0]; if (f) processFile(f) }} />

//           <div
//             onClick={() => isIdle && fileRef.current?.click()}
//             onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
//             onDragLeave={() => setDragOver(false)}
//             onDrop={onDrop}
//             style={{
//               border: `1.5px ${isIdle ? 'dashed' : 'solid'} ${dragOver ? '#1a73e8' : isIdle ? 'rgba(26,115,232,0.25)' : 'rgba(26,115,232,0.15)'}`,
//               borderRadius: 14,
//               padding: isProcessing || phase === 'done' ? '18px 22px' : '40px 24px',
//               textAlign: 'center',
//               background: dragOver ? 'rgba(232,240,254,0.9)' : 'rgba(255,255,255,0.75)',
//               backdropFilter: 'blur(12px)',
//               WebkitBackdropFilter: 'blur(12px)',
//               cursor: isIdle ? 'pointer' : 'default',
//               transition: 'all 0.18s',
//             }}
//           >
//             {isIdle && (
//               <>
//                 <div style={{
//                   width: 44, height: 44, borderRadius: '50%',
//                   background: '#e8f0fe',
//                   display: 'flex', alignItems: 'center', justifyContent: 'center',
//                   margin: '0 auto 14px',
//                 }}>
//                   <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
//                     <path d="M12 15V5M12 5l-3.5 3.5M12 5l3.5 3.5" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
//                     <path d="M20 17v1a2 2 0 01-2 2H6a2 2 0 01-2-2v-1" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round"/>
//                   </svg>
//                 </div>
//                 <p style={{ fontSize: 15, fontWeight: 500, color: '#1a1a2e', margin: '0 0 4px' }}>
//                   Drop your meeting recording here
//                 </p>
//                 <p style={{ fontSize: 13, color: '#9aa0a6', margin: 0 }}>MP4 · MP3 · WAV · M4A · MPEG</p>
//               </>
//             )}

//             {phase === 'uploading' && (
//               <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
//                 <div style={{
//                   width: 18, height: 18, borderRadius: '50%',
//                   border: '2px solid #1a73e8', borderTopColor: 'transparent',
//                   animation: 'spin 0.7s linear infinite', flexShrink: 0,
//                 }} />
//                 <span style={{ fontSize: 14, color: '#5f6368' }}>
//                   Uploading <strong style={{ color: '#1a1a2e' }}>{file?.name}</strong>
//                 </span>
//               </div>
//             )}

//             {(phase === 'processing' || phase === 'done') && (
//               <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
//                 <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
//                   <path d="M9 18V6l12-3v13" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
//                   <circle cx="6" cy="18" r="3" stroke="#1a73e8" strokeWidth="1.8"/>
//                   <circle cx="18" cy="15" r="3" stroke="#1a73e8" strokeWidth="1.8"/>
//                 </svg>
//                 <span style={{ fontSize: 14, color: '#3c4043', fontWeight: 500 }}>{file?.name}</span>
//                 <span style={{ fontSize: 12, color: '#9aa0a6', marginLeft: 'auto' }}>
//                   {file ? (file.size / 1024 / 1024).toFixed(1) + ' MB' : ''}
//                 </span>
//               </div>
//             )}
//           </div>
//         </div>

//         {error && <p style={{ fontSize: 13, color: '#d93025', marginTop: 10 }}>{error}</p>}

//         {/* Narration log */}
//         {lines.length > 0 && (
//           <div style={{
//             width: '100%', maxWidth: 560,
//             marginTop: 20,
//             borderLeft: '2px solid rgba(26,115,232,0.2)',
//             paddingLeft: 18,
//           }}>
//             {lines.map((line, i) => {
//               const isLast = i === lines.length - 1 && phase !== 'done'
//               return (
//                 <div key={line.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 8 }}>
//                   <div style={{
//                     width: 7, height: 7, borderRadius: '50%', flexShrink: 0, marginTop: 6,
//                     background: isLast ? 'transparent' : '#1a73e8',
//                     border: isLast ? '1.5px solid #1a73e8' : 'none',
//                   }} />
//                   <p style={{
//                     margin: 0, fontSize: 14, lineHeight: 1.5,
//                     color: isLast ? '#1a1a2e' : '#9aa0a6',
//                     fontWeight: isLast ? 500 : 400,
//                   }}>
//                     {line.text}
//                   </p>
//                 </div>
//               )
//             })}
//             {phase === 'done' && (
//               <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4 }}>
//                 <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#1a73e8' }} />
//                 <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#1a73e8' }}>Nio is ready</p>
//               </div>
//             )}
//           </div>
//         )}

//         {/* Tools glassmorphism panel — wider than upload box */}
//         {isIdle && (
//           <div style={{
//             width: '100%', maxWidth: 760,
//             marginTop: 28,
//             background: 'rgba(255,255,255,0.55)',
//             backdropFilter: 'blur(20px)',
//             WebkitBackdropFilter: 'blur(20px)',
//             border: '1px solid rgba(26,115,232,0.12)',
//             borderRadius: 16,
//             padding: '22px 28px 18px',
//           }}>
//             <p style={{ fontSize: 11, color: '#9aa0a6', margin: '0 0 18px', letterSpacing: '0.05em' }}>
//               Available tools
//             </p>
//             <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px 40px' }}>
//               {TOOLS.map((t, i) => (
//                 <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
//                   <span style={{ fontSize: 15, color: '#1a73e8', marginTop: 1, flexShrink: 0 }}>{t.icon}</span>
//                   <div>
//                     <p style={{ margin: '0 0 2px', fontSize: 13, fontWeight: 500, color: '#1a1a2e' }}>{t.label}</p>
//                     <p style={{ margin: 0, fontSize: 12, color: '#9aa0a6' }}>{t.desc}</p>
//                   </div>
//                 </div>
//               ))}
//             </div>
//             <div style={{ marginTop: 18, paddingTop: 16, borderTop: '1px solid rgba(26,115,232,0.08)', display: 'flex', justifyContent: 'flex-end' }}>
//               <button style={{
//                 fontSize: 13, color: '#1a73e8',
//                 background: 'none',
//                 border: '1px solid rgba(26,115,232,0.3)',
//                 borderRadius: 20, padding: '6px 18px',
//                 cursor: 'pointer', fontFamily: 'inherit',
//                 transition: 'all 0.15s',
//               }}
//                 onMouseEnter={e => { e.currentTarget.style.background = '#e8f0fe' }}
//                 onMouseLeave={e => { e.currentTarget.style.background = 'none' }}
//               >
//                 Create tool
//               </button>
//             </div>
//           </div>
//         )}
//       </div>

//       <Clock />

//       <style>{`
//         @keyframes spin { to { transform: rotate(360deg); } }
//       `}</style>
//     </div>
//   )
// }
// src/pages/UploadScreen.jsx
import { useState, useRef, useCallback, useEffect } from 'react'
import { uploadMeeting, streamStatus } from '../lib/api'

const ALLOWED = ['.mp4', '.mp3', '.wav', '.m4a', '.mpeg', '.mpg']

const TOOLS = [
  {
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M9 11l3 3L22 4" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    label: 'Task extractor',
    sub: 'Action items and owners',
    desc: 'Every action item and owner',
  },
  {
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="4" width="18" height="18" rx="2" stroke="#1a73e8" strokeWidth="1.8"/>
        <path d="M16 2v4M8 2v4M3 10h18" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round"/>
        <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01" stroke="#1a73e8" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    ),
    label: 'Deadline tracker',
    sub: 'Dates resolved',
    desc: 'Specific and vague dates resolved',
  },
  {
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" stroke="#1a73e8" strokeWidth="1.8"/>
        <path d="M9 12l2 2 4-4" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    label: 'Decision log',
    sub: 'What was agreed',
    desc: 'What was agreed and by whom',
  },
  {
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    label: 'Priority brief',
    sub: 'Top 3 to act on',
    desc: 'Three things to act on now',
  },
]

const HEADLINES = [
  'Shall we tackle a session?',
  'What did the team decide?',
  'Who owns what from that call?',
  'Ready to debrief the meeting?',
  "Let's get the room on record.",
]

const NARRATION = {
  transcribing: (msg) => msg?.includes('elapsed')
    ? `Still transcribing — ${msg.match(/\((.+)\)/)?.[1] || ''} in.`
    : 'Reading through the audio now...',
  transcribed:  () => 'Got the full transcript. Going through what happened.',
  tasks:        () => 'Pulling out every action item and who owns it.',
  deadlines:    () => 'Checking for dates — firm ones and the vague kind.',
  decisions:    () => 'Logging what was actually decided, not just discussed.',
  brief:        () => 'Figuring out the three things you need to move on now.',
  saving:       () => 'Writing everything to memory.',
  embedding:    () => 'Building my knowledge of this meeting. Almost there.',
  ready:        () => 'Done. Ask me anything.',
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
    <div style={{ position: 'fixed', bottom: 24, left: 24, zIndex: 20 }}>
      <p style={{ margin: 0, fontSize: 11, color: '#9aa0a6', letterSpacing: '0.04em' }}>{date}</p>
      <p style={{ margin: 0, fontSize: 18, fontWeight: 500, color: '#3c4043', letterSpacing: '-0.5px', lineHeight: 1.2 }}>{time}</p>
    </div>
  )
}

function ArcBackground() {
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 0, overflow: 'hidden', pointerEvents: 'none' }}>
      <svg width="100%" height="100%" viewBox="0 0 1000 1000"
        preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg"
        style={{ position: 'absolute', inset: 0 }}>
        <style>{`
          @keyframes arcSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
          .arc-group { transform-origin: 820px 500px; animation: arcSpin 28s linear infinite; }
          .arc-group-2 { transform-origin: 820px 500px; animation: arcSpin 40s linear infinite reverse; }
        `}</style>
        <g className="arc-group">
          {[180,220,260,300,340,380,420,460,500,540].map((r, i) => (
            <circle key={i} cx="820" cy="500" r={r} fill="none"
              stroke={`rgba(26,115,232,${0.04 + i * 0.008})`} strokeWidth="1"
              strokeDasharray={`${r * 0.9} ${r * 5.37}`} />
          ))}
        </g>
        <g className="arc-group-2">
          {[200,250,300,350,400,450].map((r, i) => (
            <circle key={i} cx="820" cy="500" r={r} fill="none"
              stroke={`rgba(26,115,232,${0.03 + i * 0.005})`} strokeWidth="0.8"
              strokeDasharray={`${r * 0.6} ${r * 5.8}`} strokeDashoffset={r * 1.2} />
          ))}
        </g>
      </svg>
    </div>
  )
}

function TypingHeadline() {
  const [headlineIndex, setHeadlineIndex] = useState(0)
  const [displayed, setDisplayed] = useState('')
  const [typing, setTyping] = useState(true)
  const timeoutRef = useRef(null)

  useEffect(() => {
    const full = HEADLINES[headlineIndex]
    if (typing) {
      if (displayed.length < full.length) {
        timeoutRef.current = setTimeout(() => {
          setDisplayed(full.slice(0, displayed.length + 1))
        }, 38)
      } else {
        timeoutRef.current = setTimeout(() => setTyping(false), 3 * 60 * 1000)
      }
    } else {
      if (displayed.length > 0) {
        timeoutRef.current = setTimeout(() => {
          setDisplayed(prev => prev.slice(0, -1))
        }, 22)
      } else {
        setHeadlineIndex(i => (i + 1) % HEADLINES.length)
        setTyping(true)
      }
    }
    return () => clearTimeout(timeoutRef.current)
  }, [displayed, typing, headlineIndex])

  return (
    <h1 style={{
      fontSize: 30, fontWeight: 500, color: '#1a1a2e',
      margin: '0 0 8px', letterSpacing: '-0.5px', minHeight: 40,
    }}>
      {displayed}
      <span style={{
        display: 'inline-block', width: 2, height: '1em',
        background: '#1a73e8', marginLeft: 2, verticalAlign: 'text-bottom',
        animation: 'blink 1s step-end infinite',
      }} />
    </h1>
  )
}

export default function UploadScreen({ onReady, lastMeetingId }) {
  const [phase, setPhase]       = useState('idle')
  const [lines, setLines]       = useState([])
  const [dragOver, setDragOver] = useState(false)
  const [error, setError]       = useState(null)
  const [file, setFile]         = useState(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const fileRef = useRef(null)

  const addLine = useCallback((text) => {
    setLines(prev => [...prev, { text, id: Date.now() + Math.random() }])
  }, [])

  const processFile = useCallback(async (f) => {
    const ext = '.' + f.name.split('.').pop().toLowerCase()
    if (!ALLOWED.includes(ext)) {
      setError(`Unsupported format. Accepted: ${ALLOWED.join(' ')}`)
      return
    }
    setError(null)
    setFile(f)
    setLines([])
    setPhase('uploading')

    let meetingId
    try {
      const res = await uploadMeeting(f)
      meetingId = res.meeting_id
    } catch (e) {
      setError(e.message)
      setPhase('idle')
      return
    }

    setPhase('processing')
    streamStatus(
      meetingId,
      (event) => {
        const narrate = NARRATION[event.step]
        if (narrate) addLine(narrate(event.message || ''))
      },
      () => { setPhase('done'); setTimeout(() => onReady(meetingId), 600) },
      () => { setError('Lost connection.'); setPhase('idle') }
    )
  }, [onReady, addLine])

  const onDrop = (e) => {
    e.preventDefault(); setDragOver(false)
    const f = e.dataTransfer.files?.[0]
    if (f) processFile(f)
  }

  const isIdle       = phase === 'idle'
  const isProcessing = phase === 'processing' || phase === 'uploading'

  return (
    <div style={{
      minHeight: '100vh',
      background: '#f0f4ff',
      fontFamily: "'Google Sans', system-ui, sans-serif",
      position: 'relative',
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600&display=swap');
        * { box-sizing: border-box; }
        @keyframes spin  { to { transform: rotate(360deg); } }
        @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }
      `}</style>

      <ArcBackground />

      {/* ── Nav ── */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 30,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '18px 28px',
        background: 'rgba(240,244,255,0.85)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(26,115,232,0.08)',
      }}>
        <span style={{ fontSize: 17, fontWeight: 600, color: '#1a1a2e', letterSpacing: '-0.3px' }}>meetcore</span>
        <button
          onClick={() => setMenuOpen(o => !o)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, lineHeight: 0 }}
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M3 5h14M3 10h14M3 15h14" stroke="#5f6368" strokeWidth="1.4" strokeLinecap="round"/>
          </svg>
        </button>
      </nav>

      {/* ── Slide-out menu ── */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, width: 260,
        background: 'rgba(255,255,255,0.95)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderLeft: '1px solid rgba(26,115,232,0.1)',
        boxShadow: '-8px 0 32px rgba(26,115,232,0.08)',
        zIndex: 50,
        transform: menuOpen ? 'translateX(0)' : 'translateX(100%)',
        transition: 'transform 0.25s cubic-bezier(0.4,0,0.2,1)',
        display: 'flex', flexDirection: 'column',
        padding: '24px 0',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 20px 20px',
          borderBottom: '1px solid rgba(26,115,232,0.08)',
        }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: '#1a1a2e' }}>meetcore</span>
          <button onClick={() => setMenuOpen(false)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, lineHeight: 0 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6l12 12" stroke="#5f6368" strokeWidth="1.6" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        <div style={{ padding: '20px 20px 8px' }}>
          <p style={{ fontSize: 10, color: '#9aa0a6', margin: '0 0 12px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            Tools
          </p>
          {TOOLS.map((t, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '10px 12px', borderRadius: 10, marginBottom: 2,
              cursor: 'pointer', transition: 'background 0.15s',
            }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(26,115,232,0.06)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <div style={{
                width: 28, height: 28, borderRadius: 7, background: '#e8f0fe',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                {t.icon}
              </div>
              <div>
                <p style={{ margin: 0, fontSize: 13, fontWeight: 500, color: '#1a1a2e' }}>{t.label}</p>
                <p style={{ margin: 0, fontSize: 11, color: '#9aa0a6' }}>{t.sub}</p>
              </div>
            </div>
          ))}
        </div>

        <div style={{ padding: '12px 20px 8px', borderTop: '1px solid rgba(26,115,232,0.06)', marginTop: 8 }}>
          <p style={{ fontSize: 10, color: '#9aa0a6', margin: '0 0 12px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            Recents
          </p>
          {lastMeetingId ? (
            <div
              onClick={() => { onReady(lastMeetingId); setMenuOpen(false) }}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '10px 12px', borderRadius: 10, cursor: 'pointer', transition: 'background 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(26,115,232,0.06)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M9 18V6l12-3v13" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="6" cy="18" r="3" stroke="#1a73e8" strokeWidth="1.8"/>
                <circle cx="18" cy="15" r="3" stroke="#1a73e8" strokeWidth="1.8"/>
              </svg>
              <span style={{ fontSize: 13, color: '#1a73e8', fontWeight: 500 }}>Last session</span>
            </div>
          ) : (
            <p style={{ fontSize: 12, color: '#c4c7c9', padding: '0 12px', margin: 0 }}>No sessions yet</p>
          )}
        </div>
      </div>

      {/* Backdrop */}
      {menuOpen && (
        <div onClick={() => setMenuOpen(false)} style={{
          position: 'fixed', inset: 0, zIndex: 40,
          background: 'rgba(0,0,0,0.08)',
        }} />
      )}

      {/* ── Main content ── */}
      <div style={{
        minHeight: '100vh',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: '100px 80px 80px',
        position: 'relative', zIndex: 10,
      }}>

        {isIdle && (
          <div style={{ marginBottom: 28, textAlign: 'center' }}>
            <TypingHeadline />
            <p style={{ fontSize: 15, color: '#5f6368', margin: 0 }}>
              Drop in a recording — Nio will read it and be ready to answer anything.
            </p>
          </div>
        )}

        {/* Upload box */}
        <div style={{ width: '100%', maxWidth: 560 }}>
          <input ref={fileRef} type="file" accept={ALLOWED.join(',')} style={{ display: 'none' }}
            onChange={e => { const f = e.target.files?.[0]; if (f) processFile(f) }} />

          <div
            onClick={() => isIdle && fileRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            style={{
              border: `1.5px ${isIdle ? 'dashed' : 'solid'} ${dragOver ? '#1a73e8' : isIdle ? 'rgba(26,115,232,0.25)' : 'rgba(26,115,232,0.15)'}`,
              borderRadius: 14,
              padding: isProcessing || phase === 'done' ? '18px 22px' : '40px 24px',
              textAlign: 'center',
              background: dragOver ? 'rgba(232,240,254,0.9)' : 'rgba(255,255,255,0.75)',
              backdropFilter: 'blur(12px)',
              WebkitBackdropFilter: 'blur(12px)',
              cursor: isIdle ? 'pointer' : 'default',
              transition: 'all 0.18s',
              boxShadow: '0 4px 24px rgba(26,115,232,0.10), 0 1px 4px rgba(26,115,232,0.06)',
            }}
          >
            {isIdle && (
              <>
                <div style={{
                  width: 44, height: 44, borderRadius: '50%',
                  background: '#e8f0fe',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  margin: '0 auto 14px',
                }}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path d="M12 15V5M12 5l-3.5 3.5M12 5l3.5 3.5" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M20 17v1a2 2 0 01-2 2H6a2 2 0 01-2-2v-1" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round"/>
                  </svg>
                </div>
                <p style={{ fontSize: 15, fontWeight: 500, color: '#1a1a2e', margin: '0 0 4px' }}>
                  Drop your meeting recording here
                </p>
                <p style={{ fontSize: 13, color: '#9aa0a6', margin: 0 }}>MP4 · MP3 · WAV · M4A · MPEG</p>
              </>
            )}

            {phase === 'uploading' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{
                  width: 18, height: 18, borderRadius: '50%',
                  border: '2px solid #1a73e8', borderTopColor: 'transparent',
                  animation: 'spin 0.7s linear infinite', flexShrink: 0,
                }} />
                <span style={{ fontSize: 14, color: '#5f6368' }}>
                  Uploading <strong style={{ color: '#1a1a2e' }}>{file?.name}</strong>
                </span>
              </div>
            )}

            {(phase === 'processing' || phase === 'done') && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
                  <path d="M9 18V6l12-3v13" stroke="#1a73e8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                  <circle cx="6" cy="18" r="3" stroke="#1a73e8" strokeWidth="1.8"/>
                  <circle cx="18" cy="15" r="3" stroke="#1a73e8" strokeWidth="1.8"/>
                </svg>
                <span style={{ fontSize: 14, color: '#3c4043', fontWeight: 500 }}>{file?.name}</span>
                <span style={{ fontSize: 12, color: '#9aa0a6', marginLeft: 'auto' }}>
                  {file ? (file.size / 1024 / 1024).toFixed(1) + ' MB' : ''}
                </span>
              </div>
            )}
          </div>
        </div>

        {error && <p style={{ fontSize: 13, color: '#d93025', marginTop: 10 }}>{error}</p>}

        {/* Narration log */}
        {lines.length > 0 && (
          <div style={{
            width: '100%', maxWidth: 560, marginTop: 20,
            borderLeft: '2px solid rgba(26,115,232,0.2)', paddingLeft: 18,
          }}>
            {lines.map((line, i) => {
              const isLast = i === lines.length - 1 && phase !== 'done'
              return (
                <div key={line.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 8 }}>
                  <div style={{
                    width: 7, height: 7, borderRadius: '50%', flexShrink: 0, marginTop: 6,
                    background: isLast ? 'transparent' : '#1a73e8',
                    border: isLast ? '1.5px solid #1a73e8' : 'none',
                  }} />
                  <p style={{
                    margin: 0, fontSize: 14, lineHeight: 1.5,
                    color: isLast ? '#1a1a2e' : '#9aa0a6',
                    fontWeight: isLast ? 500 : 400,
                  }}>
                    {line.text}
                  </p>
                </div>
              )
            })}
            {phase === 'done' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4 }}>
                <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#1a73e8' }} />
                <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#1a73e8' }}>Nio is ready</p>
              </div>
            )}
          </div>
        )}

        {/* Tools panel */}
        {isIdle && (
          <div style={{
            width: '100%', maxWidth: 760, marginTop: 28,
            background: 'rgba(255,255,255,0.55)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            border: '1px solid rgba(26,115,232,0.12)',
            borderRadius: 16,
            padding: '22px 28px 18px',
            boxShadow: '0 4px 24px rgba(26,115,232,0.10), 0 1px 4px rgba(26,115,232,0.06)',
          }}>
            <p style={{ fontSize: 11, color: '#9aa0a6', margin: '0 0 18px', letterSpacing: '0.05em' }}>
              Available tools
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px 40px' }}>
              {TOOLS.map((t, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                  <div style={{
                    width: 30, height: 30, borderRadius: 8, background: '#e8f0fe',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0, marginTop: 1,
                  }}>
                    {t.icon}
                  </div>
                  <div>
                    <p style={{ margin: '0 0 2px', fontSize: 13, fontWeight: 500, color: '#1a1a2e' }}>{t.label}</p>
                    <p style={{ margin: 0, fontSize: 12, color: '#9aa0a6' }}>{t.desc}</p>
                  </div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 18, paddingTop: 16, borderTop: '1px solid rgba(26,115,232,0.08)', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                style={{
                  fontSize: 13, color: '#1a73e8', background: 'none',
                  border: '1px solid rgba(26,115,232,0.3)',
                  borderRadius: 20, padding: '6px 18px',
                  cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.15s',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = '#e8f0fe' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'none' }}
              >
                Create tool
              </button>
            </div>
          </div>
        )}
      </div>

      <Clock />
    </div>
  )
}