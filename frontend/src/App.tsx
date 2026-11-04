import { useEffect, useState } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { apiGet } from './services/api'
import './App.css'

function App() {
  const [apiStatus, setApiStatus] = useState('checking…')
  const { status: wsStatus } = useWebSocket()

  useEffect(() => {
    apiGet<{ status: string }>('/health')
      .then((data) => setApiStatus(data.status))
      .catch(() => setApiStatus('unreachable'))
  }, [])

  return (
    <main className="app">
      <h1>TikTok Live Game</h1>
      <ul className="status">
        <li>API: {apiStatus}</li>
        <li>WebSocket: {wsStatus}</li>
      </ul>
    </main>
  )
}

export default App
