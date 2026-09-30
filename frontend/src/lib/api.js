const BASE = '/api'

export async function uploadMeeting(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Upload failed')
  }
  return res.json() // { meeting_id, status, message }
}

export function streamStatus(meetingId, onEvent, onDone, onError) {
  let lastEventCount = 0
  let stopped = false

  const poll = async () => {
    try {
      const res = await fetch(`/api/upload/status/${meetingId}`)
      if (!res.ok) throw new Error('Status check failed')
      const data = await res.json()

      // Emit only new events since last poll
      const newEvents = data.events.slice(lastEventCount)
      lastEventCount = data.events.length
      newEvents.forEach(onEvent)

      if (data.is_complete) {
        onDone(data)
        return
      }

      if (!stopped) setTimeout(poll, 1500)
    } catch (e) {
      if (!stopped) onError(e)
    }
  }

  poll()
  return () => { stopped = true }
}

// Unified askNio supporting optional history
export async function askNio(meetingId, question, history = []) {
  const res = await fetch(`${BASE}/nio/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ meeting_id: meetingId, question, history }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Nio error')
  }
  return res.json() // { answer, strategy_used }
}

// --- TTS (Text-to-Speech) ---
export async function speak(text, voice = 'hannah') {
  const res = await fetch(`${BASE}/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, voice }),
  })
  if (!res.ok) throw new Error('TTS failed')
  return res.blob() // audio/wav blob
}

// --- STT (Speech-to-Text) ---
export async function transcribeAudio(audioBlob) {
  const form = new FormData()
  form.append('file', audioBlob, 'recording.wav')
  
  const res = await fetch(`${BASE}/stt`, { 
    method: 'POST', 
    body: form 
  })
  
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'STT transcription failed')
  }
  
  return res.json() // { text }
}

export async function getRealtimeToken() {
  const res = await fetch(`${BASE}/realtime-token`, { method: 'POST' })
  if (!res.ok) throw new Error('Could not get realtime token')
  return res.json() // { token }
}