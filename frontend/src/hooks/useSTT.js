import { useRef, useState, useCallback } from 'react'
import { getRealtimeToken } from '../lib/api'

/**
 * useSTT — Speech-to-text hook
 * Primary: AssemblyAI RealtimeTranscriber (via temp token from backend)
 * Fallback: Web Speech API (Chrome/Edge only)
 *
 * Returns: { transcript, isListening, startListening, stopListening, error }
 */
export function useSTT({ onFinalTranscript }) {
  const [transcript, setTranscript] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [error, setError] = useState(null)

  const assemblyRef = useRef(null)
  const webSpeechRef = useRef(null)
  const streamRef = useRef(null)
  const modeRef = useRef('idle') // 'assemblyai' | 'webspeech' | 'idle'

  // ── AssemblyAI path ────────────────────────────────────────────────────────
  const startAssemblyAI = useCallback(async () => {
    try {
      const { token } = await getRealtimeToken()
      const { RealtimeTranscriber } = await import('assemblyai')

      const rt = new RealtimeTranscriber({
        token,
        sampleRate: 16000,
        wordBoost: [],
      })

      rt.on('transcript.partial', (t) => {
        setTranscript(t.text || '')
      })

      rt.on('transcript.final', (t) => {
        const text = t.text || ''
        setTranscript(text)
        if (text.trim()) onFinalTranscript(text)
      })

      rt.on('error', (err) => {
        console.warn('[STT] AssemblyAI error, falling back:', err)
        stopAssemblyAI()
        startWebSpeech()
      })

      await rt.connect()
      assemblyRef.current = rt

      // Mic stream → AssemblyAI
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const ctx = new AudioContext({ sampleRate: 16000 })
      const source = ctx.createMediaStreamSource(stream)
      const processor = ctx.createScriptProcessor(4096, 1, 1)

      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0)
        const pcm = new Int16Array(input.length)
        for (let i = 0; i < input.length; i++) {
          pcm[i] = Math.max(-32768, Math.min(32767, input[i] * 32768))
        }
        rt.sendAudio(pcm.buffer)
      }

      source.connect(processor)
      processor.connect(ctx.destination)
      modeRef.current = 'assemblyai'

      return true
    } catch (err) {
      console.warn('[STT] AssemblyAI init failed, falling back:', err)
      return false
    }
  }, [onFinalTranscript])

  const stopAssemblyAI = useCallback(async () => {
    if (assemblyRef.current) {
      try { await assemblyRef.current.close() } catch {}
      assemblyRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
  }, [])

  // ── Web Speech API fallback ────────────────────────────────────────────────
  const startWebSpeech = useCallback(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setError('Speech recognition not supported in this browser.')
      setIsListening(false)
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onresult = (e) => {
      let interim = ''
      let final = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const text = e.results[i][0].transcript
        if (e.results[i].isFinal) final += text
        else interim += text
      }
      setTranscript(interim || final)
      if (final.trim()) onFinalTranscript(final.trim())
    }

    recognition.onerror = (e) => {
      setError(`Speech error: ${e.error}`)
      setIsListening(false)
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognition.start()
    webSpeechRef.current = recognition
    modeRef.current = 'webspeech'
  }, [onFinalTranscript])

  const stopWebSpeech = useCallback(() => {
    if (webSpeechRef.current) {
      webSpeechRef.current.stop()
      webSpeechRef.current = null
    }
  }, [])

  // ── Public interface ───────────────────────────────────────────────────────
  const startListening = useCallback(async () => {
    setError(null)
    setTranscript('')
    setIsListening(true)

    const ok = await startAssemblyAI()
    if (!ok) startWebSpeech()
  }, [startAssemblyAI, startWebSpeech])

  const stopListening = useCallback(async () => {
    setIsListening(false)
    if (modeRef.current === 'assemblyai') await stopAssemblyAI()
    else stopWebSpeech()
    modeRef.current = 'idle'
  }, [stopAssemblyAI, stopWebSpeech])

  return { transcript, isListening, startListening, stopListening, error }
}
