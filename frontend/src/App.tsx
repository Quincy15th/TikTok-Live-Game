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
  const { status, lastMessage } = useWebSocket<GameMessage>()

  useEffect(() => {
    apiGet<GameState>('/game/state')
      .then(setState)
      .catch(() => setFeedback('Không thể kết nối backend. Hãy chạy FastAPI ở cổng 8000.'))
  }, [])

  useEffect(() => {
    if (lastMessage?.type === 'game_state' && lastMessage.data) setState(lastMessage.data)
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
      setFeedback(result.accepted ? '+10 điểm! Chính xác 🎉' : ({
        incorrect: 'Chưa đúng, thử lại nhé!',
        already_correct: 'Bạn đã trả lời đúng câu này rồi.',
        time_up: 'Hết giờ cho câu này.',
      }[result.reason ?? ''] ?? 'Chưa ghi nhận đáp án.'))
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
          <span>Chế độ chơi thử • Chưa kết nối TikTok LIVE</span>
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
          <span>Demo Mode • Kết nối TikTok LIVE sẽ được bổ sung sau</span>
        </footer>
      </section>

      <aside className="controls">
        <div className="control-top">
          <span className="mode-pill">DEMO MODE</span>
          <span className={status === 'open' ? 'connection online' : 'connection'}>
            ● WebSocket: {status}
          </span>
        </div>
        <h2>Điều khiển trò chơi</h2>
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
