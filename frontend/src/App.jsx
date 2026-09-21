// src/App.jsx
import { useState } from 'react'
import UploadScreen from './pages/UploadScreen'
import NioScreen from './pages/NioScreen'

export default function App() {
  const [screen, setScreen] = useState('upload')
  const [meetingId, setMeetingId] = useState(null)

  const handleReady = (id) => { setMeetingId(id); setScreen('nio') }
  const handleEnd = () => { setScreen('upload') }
  // meetingId NOT cleared on end — so upload screen nio icon still works

  if (screen === 'nio' && meetingId)
    return <NioScreen meetingId={meetingId} onEnd={handleEnd} />
  return <UploadScreen onReady={handleReady} lastMeetingId={meetingId} />
}