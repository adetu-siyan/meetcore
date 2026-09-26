import React from 'react'

export function CalendarPanel({ content, dark, onComplete }) {
  React.useEffect(() => {
    if (onComplete) {
      setTimeout(onComplete, 300)
    }
  }, [onComplete])

  const th = dark ? {
    bg: '#1a1a2e', text: '#e2e8f0', label: '#94a3b8', border: 'rgba(255,255,255,0.08)',
    input: '#0f172a', button: '#6366f1', buttonHover: '#4f46e5',
    card: '#1e1e38', accent: '#6366f1'
  } : {
    bg: '#ffffff', text: '#0f172a', label: '#64748b', border: '#e2e8f0',
    input: '#f8fafc', button: '#2563eb', buttonHover: '#1d4ed8',
    card: '#f1f5f9', accent: '#3b82f6'
  }

  // Parse the content, falling back to defaults if parsing fails
  const data = typeof content === 'string' ? JSON.parse(content || '{}') : (content || {})
  
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ 
        padding: '24px', borderBottom: `1px solid ${th.border}`, 
        display: 'flex', alignItems: 'center', justifyContent: 'space-between'
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: th.text }}>Schedule Meeting</h2>
          <p style={{ margin: '4px 0 0', fontSize: 13, color: th.label }}>Google Calendar Invite Draft</p>
        </div>
        <button style={{
          background: th.button, color: '#fff', border: 'none', 
          padding: '8px 16px', borderRadius: 6, fontSize: 13, fontWeight: 500,
          cursor: 'pointer'
        }}>
          Send Invite
        </button>
      </div>

      <div className="panel-scroll" style={{ padding: '24px', flex: 1, overflowY: 'auto' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          
          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: th.label, marginBottom: 6 }}>EVENT TITLE</label>
              <input 
                type="text" 
                defaultValue={data.title || "Follow-up Meeting"} 
                style={{
                  width: '100%', padding: '10px 12px', borderRadius: 6,
                  border: `1px solid ${th.border}`, background: th.input, color: th.text,
                  fontSize: 14, outline: 'none'
                }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: th.label, marginBottom: 6 }}>DATE & TIME</label>
              <input 
                type="text" 
                defaultValue={data.time || "Next Tuesday, 2:00 PM"} 
                style={{
                  width: '100%', padding: '10px 12px', borderRadius: 6,
                  border: `1px solid ${th.border}`, background: th.input, color: th.text,
                  fontSize: 14, outline: 'none'
                }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: th.label, marginBottom: 6 }}>GUESTS</label>
              <input 
                type="text" 
                defaultValue={data.guests || "emmanuel@meetcore.com"} 
                style={{
                  width: '100%', padding: '10px 12px', borderRadius: 6,
                  border: `1px solid ${th.border}`, background: th.input, color: th.text,
                  fontSize: 14, outline: 'none'
                }}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: th.label, marginBottom: 6 }}>AGENDA / NOTES</label>
            <textarea 
              defaultValue={data.agenda || "- Review deployment plan\n- Finalize Q4 budget"} 
              style={{
                width: '100%', padding: '12px', borderRadius: 6, minHeight: '120px',
                border: `1px solid ${th.border}`, background: th.input, color: th.text,
                fontSize: 14, outline: 'none', resize: 'vertical',
                lineHeight: 1.5
              }}
            />
          </div>

          <div style={{ 
            marginTop: 8, padding: 16, borderRadius: 8, 
            background: th.card, border: `1px solid ${th.border}`,
            display: 'flex', alignItems: 'flex-start', gap: 12
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" style={{ marginTop: 2 }}>
              <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14v-4z" stroke={th.accent} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <rect x="3" y="6" width="12" height="12" rx="2" stroke={th.accent} strokeWidth="2"/>
            </svg>
            <div>
              <div style={{ fontSize: 14, fontWeight: 500, color: th.text }}>Google Meet Conference</div>
              <div style={{ fontSize: 13, color: th.label, marginTop: 4 }}>Link will be generated when sent.</div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
