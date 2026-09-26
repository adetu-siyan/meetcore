import { useTypewriter } from '../hooks/useTypewriter'

export function TranscriptPanel({ content, dark, onComplete }) {
  const { displayed, done } = useTypewriter(content, !!content, onComplete)
  const tc  = dark ? 'rgba(255,255,255,0.82)' : '#1a1a2e'
  const tc2 = dark ? 'rgba(255,255,255,0.4)'  : '#9aa0a6'

  const download = () => {
    const blob = new Blob([content], { type: 'text/plain' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url; a.download = 'transcript.txt'; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{ padding: '24px 24px 20px' }}>
      <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: tc2, marginBottom: 16, marginTop: 0 }}>
        Transcript
      </p>
      <p style={{ fontSize: 14, lineHeight: 1.8, color: tc, whiteSpace: 'pre-wrap', margin: 0 }}>
        {displayed}
        {!done && <span style={{ opacity: 0.4 }}>▍</span>}
      </p>
      {done && (
        <button onClick={download} style={{
          marginTop: 16, display: 'flex', alignItems: 'center', gap: 7,
          padding: '8px 16px', borderRadius: 8,
          background: dark ? 'rgba(255,255,255,0.08)' : 'rgba(99,102,241,0.08)',
          border: `1px solid ${dark ? 'rgba(255,255,255,0.12)' : 'rgba(99,102,241,0.2)'}`,
          color: dark ? 'rgba(255,255,255,0.7)' : '#6366f1',
          fontSize: 13, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"
              stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Download
        </button>
      )}
    </div>
  )
}
