/**
 * WebSocket hook for real-time photo request updates.
 *
 * The JWT is sent as a WebSocket subprotocol value instead of a query parameter,
 * keeping bearer credentials out of reverse-proxy/access URLs.
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
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const canConnectRef = useRef(false)
  const generationRef = useRef(0)

  const connect = useCallback(() => {
    if (!canConnectRef.current || !authToken) {
      setError('No authentication token provided')
      return
    }

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws/photo-requests`

      const epoch = generationRef.current
      const ws = new WebSocket(wsUrl, ['access_token', authToken])

      ws.onopen = () => {
        if (!canConnectRef.current || generationRef.current !== epoch) return
        setConnected(true)
        setError(null)
        reconnectCountRef.current = 0
      }

      ws.onmessage = (event) => {
        if (!canConnectRef.current || generationRef.current !== epoch) return
        try {
          const data: PhotoRequestEvent = JSON.parse(event.data)
          setLastEvent(data)
          onEvent?.(data)
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.onerror = () => {
        if (canConnectRef.current && generationRef.current === epoch) {
          setError('WebSocket connection error')
        }
      }

      ws.onclose = () => {
        if (!canConnectRef.current || generationRef.current !== epoch) return
        if (wsRef.current === ws) wsRef.current = null
        setConnected(false)
        if (autoReconnect && reconnectCountRef.current < maxReconnectAttempts) {
          reconnectCountRef.current += 1
          reconnectTimeoutRef.current = setTimeout(() => {
            if (canConnectRef.current && generationRef.current === epoch) connect()
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
    canConnectRef.current = false
    generationRef.current += 1
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }
    setConnected(false)
  }, [])

  useEffect(() => {
    canConnectRef.current = Boolean(authToken)
    if (authToken) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [authToken, connect, disconnect])

  const reconnect = useCallback(() => {
    if (!authToken) return
    canConnectRef.current = true
    connect()
  }, [authToken, connect])

  return {
    connected,
    lastEvent,
    error,
    disconnect,
    reconnect
  }
}
