import { useState, useEffect, useRef } from 'react'

export function PanelShell({ dark, children, minHeight = 180, maxHeight = 'calc(100vh - 104px)' }) {
  const contentRef = useRef(null)
  const [height, setHeight] = useState(minHeight)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const media = window.matchMedia('(max-width: 768px)')
    const sync = () => setIsMobile(media.matches)
    sync()
    media.addEventListener?.('change', sync)
    return () => media.removeEventListener?.('change', sync)
  }, [])

  useEffect(() => {
    if (!contentRef.current) return
    const ro = new ResizeObserver(() => {
      const h = contentRef.current?.scrollHeight || minHeight
      setHeight(Math.min(Math.max(h + 56, minHeight), typeof maxHeight === 'number' ? maxHeight : 9999))
    })
    ro.observe(contentRef.current)
    return () => ro.disconnect()
  }, [minHeight, maxHeight])

  return (
    <div style={{
      height,
      maxHeight: isMobile ? 'min(52vh, 420px)' : maxHeight,
      minWidth: isMobile ? 0 : 320,
      maxWidth: isMobile ? 'min(92vw, 420px)' : 460,
      width: isMobile ? 'min(92vw, 420px)' : 'max-content',
      background: dark ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.92)',
      border: `1px solid ${dark ? 'rgba(255,255,255,0.10)' : 'rgba(26,115,232,0.18)'}`,
      borderRadius: 24,
      backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
      boxShadow: dark
        ? '0 8px 40px rgba(0,0,0,0.4)'
        : '0 4px 32px rgba(26,115,232,0.10), 0 2px 8px rgba(0,0,0,0.06)',
      overflow: 'hidden',
      transition: 'height 0.4s cubic-bezier(0.34,1.56,0.64,1), width 0.4s cubic-bezier(0.34,1.56,0.64,1)',
      display: 'flex', flexDirection: 'column',
    }}>
      <div ref={contentRef} style={{ flex: 1, overflowY: 'auto', minHeight: 0 }} className="panel-scroll">
        {children}
      </div>
    </div>
  )
}
