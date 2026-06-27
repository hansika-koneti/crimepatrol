import { useEffect, useRef } from 'react'
import { WS_BASE } from '@/utils/constants'
import { useAppStore } from '@/store'

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const { setLiveConnected, setPrediction, setRecommendations, token } = useAppStore()

  useEffect(() => {
    if (!token) return

    const connect = () => {
      const ws = new WebSocket(`${WS_BASE}/dashboard`)
      wsRef.current = ws

      ws.onopen = () => {
        setLiveConnected(true)
        console.info('[WS] Connected to dashboard stream')
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.event === 'prediction_update') {
            const { area_id, prediction, recommendations } = msg
            if (area_id && prediction) setPrediction(area_id, prediction)
            if (recommendations) setRecommendations(recommendations)
          }
        } catch {}
      }

      ws.onerror = () => setLiveConnected(false)

      ws.onclose = () => {
        setLiveConnected(false)
        // Reconnect after 3s
        setTimeout(connect, 3000)
      }
    }

    connect()
    const ping = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping')
      }
    }, 25000)

    return () => {
      clearInterval(ping)
      wsRef.current?.close()
    }
  }, [token])
}
