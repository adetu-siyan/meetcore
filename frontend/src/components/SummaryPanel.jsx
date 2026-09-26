import { useTypewriter } from '../hooks/useTypewriter'

export function SummaryPanel({ content, dark, onComplete }) {
  const flat = content ? [
    ...(content.key_points     || []).map(t => ({ section: 'Key Points',    text: t })),
    ...(content.decisions      || []).map(t => ({ section: 'Decisions',      text: t })),
    ...(content.open_questions || []).map(t => ({ section: 'Open Questions', text: t })),
  ] : []

  const fullText = flat.map(i => i.text).join('\n')
  const { displayed } = useTypewriter(fullText, flat.length > 0, onComplete)

  const tc  = dark ? 'rgba(255,255,255,0.82)' : '#1a1a2e'
  const tc2 = dark ? 'rgba(255,255,255,0.4)'  : '#9aa0a6'
  const ac  = dark ? 'rgba(99,102,241,0.9)'   : '#6366f1'

  let charsLeft = displayed.length
  const rendered = flat.map(item => {
    if (charsLeft <= 0) return null
    const show = item.text.slice(0, charsLeft)
    charsLeft -= item.text.length + 1
    return { ...item, show }
  }).filter(Boolean)

  return (
    <div style={{ padding: '24px 24px 20px' }}>
      <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: tc2, marginBottom: 20, marginTop: 0 }}>
        Meeting Summary
      </p>
      {['Key Points', 'Decisions', 'Open Questions'].map(section => {
        const items = rendered.filter(i => i.section === section)
        if (!items.length) return null
        return (
          <div key={section} style={{ marginBottom: 20 }}>
            <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: ac, marginBottom: 10, marginTop: 0 }}>
              {section}
            </p>
            {items.map((item, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 8 }}>
                <span style={{ color: ac, marginTop: 2, flexShrink: 0, fontSize: 12 }}>◆</span>
                <p style={{ fontSize: 14, lineHeight: 1.7, color: tc, margin: 0 }}>
                  {item.show}
                  {item.show.length < item.text.length && <span style={{ opacity: 0.4 }}>▍</span>}
                </p>
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}
