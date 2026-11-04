import { useEffect, useRef, useState } from 'react'
import { config } from '../config'

export type ConnectionStatus = 'connecting' | 'open' | 'closed'

type Options<TMessage> = {
  url?: string
  /** Called for every parsed message; preferred over reading `lastMessage` in an effect. */
  onMessage?: (message: TMessage) => void
}

const MAX_RETRY_DELAY_MS = 10_000

/**
 * Opens a WebSocket to the backend and reconnects automatically with backoff,
 * so a long-running OBS Browser Source recovers when the backend restarts.
 */
export function useWebSocket<TMessage = unknown>({ url = config.wsUrl, onMessage }: Options<TMessage> = {}) {
  const socketRef = useRef<WebSocket | null>(null)
  const onMessageRef = useRef(onMessage)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const attemptRef = useRef(0)
  const disposedRef = useRef(false)
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [lastMessage, setLastMessage] = useState<TMessage | null>(null)

  useEffect(() => {
    onMessageRef.current = onMessage
  }, [onMessage])

  useEffect(() => {
    disposedRef.current = false
    attemptRef.current = 0

    const connect = () => {
      setStatus('connecting')
      const socket = new WebSocket(url)
      socketRef.current = socket

      socket.onopen = () => {
        attemptRef.current = 0
        setStatus('open')
      }
      socket.onclose = () => {
        if (disposedRef.current) return
        setStatus('closed')
        const delay = Math.min(MAX_RETRY_DELAY_MS, 500 * 2 ** attemptRef.current++)
        retryTimerRef.current = setTimeout(connect, delay)
      }
      socket.onmessage = (event) => {
        let message: TMessage
        try {
          message = JSON.parse(event.data) as TMessage
        } catch {
          return
        }
        setLastMessage(message)
        onMessageRef.current?.(message)
      }
    }

    connect()

    return () => {
      disposedRef.current = true
      if (retryTimerRef.current !== null) clearTimeout(retryTimerRef.current)
      socketRef.current?.close()
    }
  }, [url])

  const send = (data: unknown) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(data))
    }
  }

  return { status, lastMessage, send }
}
