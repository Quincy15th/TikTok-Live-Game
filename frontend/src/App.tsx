import { useEffect, useState, type FormEvent } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { apiGet } from './services/api'
import './App.css'

type Player = { name: string; score: number; correct: number }
type Recent = { name: string; points: number }
type GameState = {
  question_number: number
  prompt: string
  length: number
  hint: string
  remaining: number
  duration: number
  leaderboard: Player[]
  recent: Recent[]
  mode: string
}
type GameMessage = { type: string; data?: GameState }
type AnswerResult = { accepted: boolean; points?: number; reason?: string }
type TikTokStatus = { status: string; username: string | null; error: string | null; comments_received: number }

async function post<T>(path: string, body: object = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json() as Promise<T>
}

function App() {
  const [state, setState] = useState<GameState | null>(null)
  const [name, setName] = useState('viewer_demo')
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState('')
  const [busy, setBusy] = useState(false)
  const [liveUser, setLiveUser] = useState('')
  const [liveStatus, setLiveStatus] = useState<TikTokStatus | null>(null)
  const [liveBusy, setLiveBusy] = useState(false)
  const { status, lastMessage } = useWebSocket<GameMessage>()

  useEffect(() => {
    apiGet<TikTokStatus>('/tiktok/status').then(setLiveStatus).catch(() => {})
    apiGet<GameState>('/game/state')
      .then(setState)
      .catch(() => setFeedback('Không thể kết nối backend. Hãy chạy FastAPI ở cổng 8000.'))
  }, [])

  useEffect(() => {
    if (lastMessage?.type === 'game_state' && lastMessage.data) setState(lastMessage.data)
    if (lastMessage?.type === 'tiktok_status' && lastMessage.data) setLiveStatus(lastMessage.data as unknown as TikTokStatus)
  }, [lastMessage])

  useEffect(() => {
    if (status === 'open') {
      apiGet<GameState>('/game/state').then(setState).catch(() => {})
    }
  }, [status])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!name.trim() || !answer.trim() || busy) return
    setBusy(true)
    try {
      const result = await post<AnswerResult>('/game/answer', { name: name.trim(), answer: answer.trim() })
      const messages: Record<string, string> = {
        incorrect: 'Chưa đúng, thử lại nhé!',
        already_correct: 'Bạn đã trả lời đúng câu này rồi.',
        time_up: 'Hết giờ cho câu này.',
      }
      setFeedback(result.accepted ? '+10 điểm! Chính xác 🎉' : (messages[result.reason ?? ''] ?? 'Chưa ghi nhận đáp án.'))
      setAnswer('')
    } catch {
      setFeedback('Không gửi được đáp án. Kiểm tra kết nối backend.')
    } finally {
      setBusy(false)
    }
  }

  async function next() {
    try {
      setState(await post<GameState>('/game/next'))
      setFeedback('Đã chuyển sang câu tiếp theo.')
    } catch {
      setFeedback('Không chuyển được câu hỏi.')
    }
  }

  async function toggleLive() {
    setLiveBusy(true)
    try {
      const active = liveStatus?.status === 'connected' || liveStatus?.status === 'connecting' || liveStatus?.status === 'reconnecting'
      const result = await post<TikTokStatus>(active ? '/tiktok/disconnect' : '/tiktok/connect', active ? {} : { username: liveUser.trim() })
      setLiveStatus(result)
      setFeedback(active ? 'Đã ngắt kết nối LIVE.' : 'Đang thử kết nối TikTok LIVE…')
    } catch {
      setFeedback('Không thể kết nối TikTok LIVE. Kiểm tra username, môi trường Python và backend logs.')
    } finally {
      setLiveBusy(false)
    }
  }

  const letters = state
    ? Array.from({ length: state.length }, (_, index) => state.hint[index] ?? '·')
    : []
  const remaining = state?.remaining ?? 0
  const progress = state ? (remaining / state.duration) * 100 : 0

  const overlayOnly = new URLSearchParams(window.location.search).has('overlay')

  return (
    <div className={overlayOnly ? 'layout overlay-only' : 'layout'}>
      <section className="overlay" aria-label="Màn hình trò chơi TikTok Live">
        <header className="live-header">
          <span className="live-mark">● DEMO LIVE</span>
          <span className="live-brand">TIKTOK QUIZ</span>
          <span className="live-viewers">✦ +10 / câu</span>
        </header>

        <div className="interaction-banner">
          <strong>🎁 QUÀ & TƯƠNG TÁC</strong>
          <span>{liveStatus?.status === 'connected' ? `Đang kết nối @${liveStatus.username} • ${liveStatus.comments_received} bình luận` : 'Chế độ Demo • Có thể kết nối TikTok LIVE trong bảng điều khiển'}</span>
        </div>

        <main className="question">
          <div className="question-id">CÂU {state?.question_number ?? '—'}</div>
          <h1>{state?.prompt ?? 'Đang kết nối…'}</h1>
          <div className="question-subtitle">tiếng Anh là gì?</div>

          <div className="timer-line">
            <span>THỜI GIAN CÒN LẠI</span>
            <b>{remaining}<small>s</small></b>
          </div>
          <div className="timer-track">
            <div className="timer-progress" style={{ width: `${progress}%` }} />
          </div>

          <div className="letters" aria-label="Gợi ý chữ cái">
            {letters.map((letter, index) => (
              <div className={index < (state?.hint.length ?? 0) ? 'letter filled' : 'letter'} key={index}>
                {letter}
              </div>
            ))}
          </div>
        </main>

        <section className="winner-panel">
          <span className="trophy">🏆</span>
          <div>
            <small>NGƯỜI TRẢ LỜI ĐÚNG GẦN NHẤT</small>
            <strong>{state?.recent[0]?.name ?? 'Chờ người chơi…'}</strong>
            <span>{state?.recent[0] ? 'Đúng đáp án • +10 điểm' : 'Hãy nhập câu trả lời để ghi điểm!'}</span>
          </div>
        </section>

        <section className="score-panels">
          <div className="score-panel">
            <h2>🏅 TOP ĐIỂM</h2>
            {(state?.leaderboard.length ?? 0) === 0 && <p>Chưa có người chơi</p>}
            {state?.leaderboard.slice(0, 5).map((player, index) => (
              <div className="score-row" key={player.name}>
                <span>{index + 1}. {player.name}</span>
                <b>{player.score}</b>
              </div>
            ))}
          </div>
          <div className="score-panel">
            <h2>✓ VỪA TRẢ LỜI ĐÚNG</h2>
            {(state?.recent.length ?? 0) === 0 && <p>Đang chờ đáp án…</p>}
            {state?.recent.map((entry, index) => (
              <div className="score-row recent-row" key={`${entry.name}-${index}`}>
                <span>{entry.name}</span><b>+{entry.points}</b>
              </div>
            ))}
          </div>
        </section>

        <footer className="overlay-footer">
          <strong>Gõ đáp án vào bình luận để chơi</strong>
          <span>{liveStatus?.status === 'connected' ? `Đang nhận bình luận từ @${liveStatus.username}` : 'Demo Mode • Chưa nhận bình luận TikTok thật'}</span>
        </footer>
      </section>

      <aside className="controls">
        <div className="control-top">
          <span className="mode-pill">DEMO MODE</span>
          <span className={status === 'open' ? 'connection online' : 'connection'}>
            ● WebSocket: {status}
          </span>
        </div>
        <h2>Kết nối TikTok LIVE</h2>
        <p>Chỉ dùng với livestream công khai đang phát. Không cần nhập mật khẩu TikTok.</p>
        <label htmlFor="live-user">TikTok username</label>
        <input id="live-user" placeholder="@username" maxLength={31} value={liveUser} onChange={(event) => setLiveUser(event.target.value)} />
        <button type="button" disabled={liveBusy || (!liveUser.trim() && !['connected','connecting','reconnecting'].includes(liveStatus?.status ?? ''))} onClick={toggleLive}>
          {['connected','connecting','reconnecting'].includes(liveStatus?.status ?? '') ? 'Ngắt kết nối LIVE' : 'Kết nối LIVE'}
        </button>
        <p role="status">TikTok: {liveStatus?.status ?? 'disconnected'} {liveStatus?.error ? `• ${liveStatus.error}` : ''}</p>
        <h2>Điều khiển trò chơi (Demo)</h2>
        <p>Giả lập bình luận TikTok để kiểm tra chấm điểm và bảng xếp hạng.</p>
        <form onSubmit={submit}>
          <label htmlFor="player">Tên người chơi</label>
          <input id="player" maxLength={40} value={name} onChange={(event) => setName(event.target.value)} />
          <label htmlFor="answer">Bình luận / đáp án</label>
          <input id="answer" maxLength={100} placeholder="Nhập đáp án tiếng Anh…" value={answer}
            onChange={(event) => setAnswer(event.target.value)} />
          <button type="submit" disabled={busy || !name.trim() || !answer.trim()}>Gửi đáp án thử</button>
        </form>
        <button className="secondary-button" onClick={next} type="button">Câu tiếp theo →</button>
        <div className="feedback" role="status">{feedback || 'Mẹo: câu đầu tiên có đáp án JACKET.'}</div>
        <div className="control-note">
          <strong>OBS / TikTok LIVE Studio</strong>
          <p>Thêm Browser Source với URL <code>http://localhost:5173/?overlay=1</code>, đặt kích thước 1080 × 1920. Trang điều khiển vẫn ở <code>http://localhost:5173</code>.</p>
        </div>
      </aside>
    </div>
  )
}

export default App
