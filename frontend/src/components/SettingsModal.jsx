import React from 'react'

export function SettingsModal({ onClose, dark }) {
  const th = dark ? {
    bg: '#0f172a', text: '#f8fafc', label: '#94a3b8', border: 'rgba(255,255,255,0.1)',
    card: '#1e293b', accent: '#6366f1', inputBg: '#020617'
  } : {
    bg: '#ffffff', text: '#0f172a', label: '#64748b', border: '#e2e8f0',
    card: '#f8fafc', accent: '#3b82f6', inputBg: '#ffffff'
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
    }}>
      <div style={{
        width: 500, background: th.bg, borderRadius: 16,
        boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
        display: 'flex', flexDirection: 'column',
        maxHeight: '90vh',
      }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px', borderBottom: `1px solid ${th.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between'
        }}>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: th.text }}>Settings</h2>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: th.label, cursor: 'pointer',
            padding: 4
          }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="panel-scroll" style={{ padding: '24px', overflowY: 'auto' }}>
          
          <section style={{ marginBottom: 32 }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', color: th.label, letterSpacing: '0.05em', marginBottom: 16 }}>Connected Apps</h3>
            
            <div style={{ 
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: 16, background: th.card, borderRadius: 12, border: `1px solid ${th.border}`,
              marginBottom: 12
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 32, height: 32, borderRadius: 6, background: '#EA4335', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 'bold' }}>G</div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 500, color: th.text }}>Google Calendar</div>
                  <div style={{ fontSize: 13, color: th.label }}>Connected as adetumosgad@gmail.com</div>
                </div>
              </div>
              <button style={{ fontSize: 13, fontWeight: 500, color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}>Disconnect</button>
            </div>

            <div style={{ 
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: 16, background: th.card, borderRadius: 12, border: `1px solid ${th.border}`
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 32, height: 32, borderRadius: 6, background: '#4A154B', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 'bold' }}>S</div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 500, color: th.text }}>Slack</div>
                  <div style={{ fontSize: 13, color: th.label }}>Not connected</div>
                </div>
              </div>
              <button style={{ fontSize: 13, fontWeight: 500, color: th.accent, background: 'none', border: 'none', cursor: 'pointer' }}>Connect</button>
            </div>
          </section>

          <section>
            <h3 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', color: th.label, letterSpacing: '0.05em', marginBottom: 16 }}>Team Directory</h3>
            <p style={{ fontSize: 13, color: th.label, marginTop: -8, marginBottom: 16, lineHeight: 1.5 }}>
              Add team members so Nio knows their email addresses when you mention them (e.g. "Send this to Emmanuel").
            </p>

            <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
              <input type="text" placeholder="Name" style={{ flex: 1, padding: '10px 12px', borderRadius: 8, border: `1px solid ${th.border}`, background: th.inputBg, color: th.text, outline: 'none' }} />
              <input type="email" placeholder="Email Address" style={{ flex: 1.5, padding: '10px 12px', borderRadius: 8, border: `1px solid ${th.border}`, background: th.inputBg, color: th.text, outline: 'none' }} />
              <button style={{ background: th.accent, color: '#fff', border: 'none', borderRadius: 8, padding: '0 16px', fontWeight: 500, cursor: 'pointer' }}>Add</button>
            </div>

            <div style={{ border: `1px solid ${th.border}`, borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ display: 'flex', alignItems: 'center', padding: '12px 16px', borderBottom: `1px solid ${th.border}` }}>
                <div style={{ flex: 1, fontSize: 14, fontWeight: 500, color: th.text }}>Emmanuel</div>
                <div style={{ flex: 1.5, fontSize: 14, color: th.label }}>emmanuel@meetcore.com</div>
                <button style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: 4 }}>×</button>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', padding: '12px 16px' }}>
                <div style={{ flex: 1, fontSize: 14, fontWeight: 500, color: th.text }}>Sarah</div>
                <div style={{ flex: 1.5, fontSize: 14, color: th.label }}>sarah@meetcore.com</div>
                <button style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: 4 }}>×</button>
              </div>
            </div>
          </section>

        </div>
      </div>
    </div>
  )
}
