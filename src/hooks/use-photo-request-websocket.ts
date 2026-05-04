/**
 * WebSocket hook for real-time photo request updates.
 * 
 * Usage:
 * ```tsx
 * const { connected, lastEvent } = usePhotoRequestWebSocket(authToken, (event) => {
 *   console.log('Photo event:', event)
 *   // Refetch list or update local state
 * })
 * ```
 */

import { useEffect, useRef, useState, useCallback } from 'react'

export interface PhotoRequestEvent {
  event: string
  photo_request_id: number
  timestamp: string
  payload: Record<string, unknown>
  user_id?: number
}

interface UsePhotoRequestWebSocketOptions {
  onEvent?: (event: PhotoRequestEvent) => void
  autoReconnect?: boolean
  reconnectDelay?: number
  maxReconnectAttempts?: number
}

export function usePhotoRequestWebSocket(
  authToken: string | null,
  options: UsePhotoRequestWebSocketOptions = {}
) {
  const {
    onEvent,
    autoReconnect = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 5
  } = options

  const [connected, setConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState<PhotoRequestEvent | null>(null)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectCountRef = useRef(0)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    if (!authToken) {
      setError('No authentication token provided')
      return
    }

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws/photo-requests?token=${encodeURIComponent(authToken)}`

      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('✅ WebSocket connected to photo-requests')
        setConnected(true)
        setError(null)
        reconnectCountRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const data: PhotoRequestEvent = JSON.parse(event.data)
          setLastEvent(data)
          onEvent?.(data)
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        setError('WebSocket connection error')
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setConnected(false)

        // Attempt reconnection
        if (autoReconnect && reconnectCountRef.current < maxReconnectAttempts) {
          reconnectCountRef.current += 1
          console.log(`Auto-reconnecting in ${reconnectDelay}ms (attempt ${reconnectCountRef.current}/${maxReconnectAttempts})`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectDelay)
        }
      }

      wsRef.current = ws
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unknown error'
      console.error('Failed to create WebSocket:', message)
      setError(message)
    }
  }, [authToken, onEvent, autoReconnect, reconnectDelay, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setConnected(false)
  }, [])

  useEffect(() => {
    if (authToken) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [authToken, connect, disconnect])

  return {
    connected,
    lastEvent,
    error,
    disconnect,
    reconnect: connect
  }
}
