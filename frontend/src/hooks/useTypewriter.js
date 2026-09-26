import { useState, useEffect, useRef } from 'react'

export function useTypewriter(target, active, onComplete, speed = 14) {
  const [displayed, setDisplayed] = useState('')
  const [done, setDone] = useState(false)
  const timerRef = useRef(null)
  const indexRef = useRef(0)
  const onCompleteRef = useRef(onComplete)
  const hasTriggeredRef = useRef(false)

  useEffect(() => { onCompleteRef.current = onComplete }, [onComplete])

  useEffect(() => {
    if (!active || !target) return
    setDisplayed('')
    setDone(false)
    indexRef.current = 0
    hasTriggeredRef.current = false
    const tick = () => {
      indexRef.current += 1
      setDisplayed(target.slice(0, indexRef.current))
      if (indexRef.current < target.length) {
        timerRef.current = setTimeout(tick, speed)
      } else {
        setDone(true)
        if (!hasTriggeredRef.current) {
          hasTriggeredRef.current = true
          if (onCompleteRef.current) onCompleteRef.current()
        }
      }
    }
    timerRef.current = setTimeout(tick, speed)
    return () => clearTimeout(timerRef.current)
  }, [target, active, speed])

  return { displayed, done }
}
