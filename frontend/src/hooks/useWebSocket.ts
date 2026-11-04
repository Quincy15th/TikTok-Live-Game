import { useEffect, useRef, useState } from 'react'
import { config } from '../config'

export type ConnectionStatus = 'connecting' | 'open' | 'closed'

/** Opens a WebSocket to the backend and exposes its status, last message and a send helper. */
export function useWebSocket<TMessage = unknown>(url: string = config.wsUrl) {
  const socketRef = useRef<WebSocket | null>(null)
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [lastMessage, setLastMessage] = useState<TMessage | null>(null)

  useEffect(() => {
    const socket = new WebSocket(url)
    socketRef.current = socket

    socket.onopen = () => setStatus('open')
    socket.onclose = () => setStatus('closed')
    socket.onmessage = (event) => setLastMessage(JSON.parse(event.data) as TMessage)

    return () => socket.close()
  }, [url])

  const send = (data: unknown) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(data))
    }
  }

  return { status, lastMessage, send }
}
