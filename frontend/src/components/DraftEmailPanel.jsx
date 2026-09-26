import { useState } from 'react'
import { useTypewriter } from '../hooks/useTypewriter'

export function DraftEmailPanel({ content, dark, onComplete }) {
  const [copied, setCopied] = useState(false)
  const subject  = content?.subject || ''
  const body     = content?.body    || ''
  const fullText = `Subject: ${subject}\n\n${body}`
  const { displayed, done } = useTypewriter(fullText, !!fullText, onComplete)

  const tc      = dark ? 'rgba(255,255,255,0.82)' : '#1a1a2e'
  const tc2     = dark ? 'rgba(255,255,255,0.4)'  : '#9aa0a6'
  const ac      = dark ? 'rgba(99,102,241,0.9)'   : '#6366f1'
  const panelBg = dark ? 'rgba(255,255,255,0.05)' : 'rgba(99,102,241,0.05)'

  const handleCopy = () => {
    navigator.clipboard.writeText(fullText).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const bodyDisplayed = displayed.slice(`Subject: ${subject}\n\n`.length)

  return (
    <div style={{ padding: '24px 24px 20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: tc2, margin: 0 }}>
          Email Draft
        </p>
        {done && (
          <button onClick={handleCopy} style={{
            fontSize: 11, fontWeight: 600, padding: '5px 12px', borderRadius: 8,
            background: copied ? ac : 'transparent',
            border: `1px solid ${copied ? ac : (dark ? 'rgba(255,255,255,0.15)' : 'rgba(99,102,241,0.3)')}`,
            color: copied ? '#fff' : ac, cursor: 'pointer', transition: 'all 0.2s',
            letterSpacing: '0.05em',
          }}>
            {copied ? 'Copied!' : 'Copy'}
          </button>
        )}
      </div>
      {subject && displayed.length > 0 && (
        <div style={{ marginBottom: 16, padding: '10px 14px', borderRadius: 10, background: panelBg }}>
          <p style={{ fontSize: 11, fontWeight: 700, color: ac, textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 4px' }}>
            Subject
          </p>
          <p style={{ fontSize: 13, color: tc, margin: 0, fontWeight: 500 }}>{subject}</p>
        </div>
      )}
      {bodyDisplayed && (
        <div style={{ padding: '10px 14px', borderRadius: 10, background: panelBg }}>
          <p style={{ fontSize: 11, fontWeight: 700, color: ac, textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 8px' }}>
            Body
          </p>
          <p style={{ fontSize: 13, lineHeight: 1.75, color: tc, margin: 0, whiteSpace: 'pre-wrap' }}>
            {bodyDisplayed}
            {!done && <span style={{ opacity: 0.4 }}>▍</span>}
          </p>
        </div>
      )}
    </div>
  )
}
