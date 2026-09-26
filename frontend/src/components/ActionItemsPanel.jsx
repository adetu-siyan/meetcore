import { useState } from 'react'
import { useTypewriter } from '../hooks/useTypewriter'

export function ActionItemsPanel({ content, dark, onComplete }) {
  const [checked, setChecked] = useState({})
  const items    = Array.isArray(content) ? content : (content?.items || [])
  const fullText = items.map(i => i.description).join('\n')
  const { displayed } = useTypewriter(fullText, items.length > 0, onComplete)

  const tc  = dark ? 'rgba(255,255,255,0.82)' : '#1a1a2e'
  const tc2 = dark ? 'rgba(255,255,255,0.4)'  : '#9aa0a6'
  const ac  = dark ? 'rgba(99,102,241,0.9)'   : '#6366f1'

  let charsLeft = displayed.length
  const visible = items.map((item, idx) => {
    if (charsLeft <= 0) return null
    const show = item.description.slice(0, charsLeft)
    charsLeft -= item.description.length + 1
    return { ...item, show, idx }
  }).filter(Boolean)

  return (
    <div style={{ padding: '24px 24px 20px' }}>
      <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: tc2, marginBottom: 20, marginTop: 0 }}>
        Action Items
      </p>
      {items.length === 0 ? (
        <p style={{ fontSize: 14, color: tc2, textAlign: 'center', margin: '24px 0' }}>
          No clear action items detected.
        </p>
      ) : (
        visible.map(({ show, idx, owner, deadline, description }) => (
          <div key={idx} style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'flex-start' }}>
            <button onClick={() => setChecked(c => ({ ...c, [idx]: !c[idx] }))} style={{
              width: 20, height: 20, borderRadius: 5, flexShrink: 0, marginTop: 2,
              border: `1.5px solid ${checked[idx] ? ac : (dark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)')}`,
              background: checked[idx] ? ac : 'transparent',
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              {checked[idx] && (
                <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
                  <path d="M2 6l3 3 5-5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </button>
            <div style={{ flex: 1 }}>
              <p style={{
                fontSize: 14, lineHeight: 1.7, color: tc, margin: 0,
                textDecoration: checked[idx] ? 'line-through' : 'none',
                opacity: checked[idx] ? 0.4 : 1, transition: 'all 0.2s',
              }}>
                {show}
                {show.length < description.length && <span style={{ opacity: 0.4 }}>▍</span>}
              </p>
              {(owner || deadline) && show.length >= description.length && (
                <p style={{ fontSize: 12, color: tc2, margin: '3px 0 0' }}>
                  {owner && <span>{owner}</span>}
                  {owner && deadline && <span style={{ margin: '0 6px' }}>·</span>}
                  {deadline && <span>{deadline}</span>}
                </p>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
