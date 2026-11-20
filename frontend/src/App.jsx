import { useEffect, useRef, useState } from 'react'
import { readChatStream, safeSourceUrl } from './chatStream.js'
import './App.css'

const suggestions = [
  { icon: 'building', title: 'Explore the collection', prompt: 'Tell me about DarGlobal and its projects.' },
  { icon: 'sparkle', title: 'Discover AIDA 360', prompt: 'What services does AIDA 360 provide?' },
  { icon: 'pin', title: 'Find a property', prompt: 'What properties are listed in Riyadh?' },
  { icon: 'compass', title: 'Get to know Wasalt', prompt: 'What is Wasalt and what does it offer?' },
]

function Icon({ name, size = 20 }) {
  const paths = {
    plus: <path d="M12 5v14M5 12h14" />,
    arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
    send: <path d="M12 19V5M6 11l6-6 6 6" />,
    stop: <rect x="7" y="7" width="10" height="10" rx="1" fill="currentColor" stroke="none" />,
    building: <><path d="M4 20h16M6 20V5l6-2v17M12 9h6v11M8.5 7v1M8.5 11v1M8.5 15v1M15 12v1M15 16v1" /></>,
    sparkle: <><path d="M12 3l1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3Z" /><path d="M19 15l.6 2.4L22 18l-2.4.6L19 21l-.6-2.4L16 18l2.4-.6L19 15Z" /></>,
    pin: <><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z" /><circle cx="12" cy="10" r="2" /></>,
    compass: <><circle cx="12" cy="12" r="9" /><path d="m15.5 8.5-2 5-5 2 2-5 5-2Z" /></>,
    link: <><path d="M13 5h6v6M19 5l-8 8" /><path d="M19 14v4a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h4" /></>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}

function Mark({ small = false }) {
  return <span className={`brand-mark${small ? ' brand-mark--small' : ''}`} aria-hidden="true">D<span>G</span></span>
}

function historyFor(turns, question) {
  const history = []
  let remaining = 12000 - question.length
  for (const turn of [...turns].reverse()) {
    if (history.length >= 10) break
    if (turn.status !== 'complete' || !turn.answer || turn.answer.length > 2000) continue
    const length = turn.question.length + turn.answer.length
    if (length > remaining) break
    remaining -= length
    history.unshift({ role: 'user', content: turn.question }, { role: 'assistant', content: turn.answer })
  }
  return history
}

function App() {
  const [turns, setTurns] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [health, setHealth] = useState('checking')
  const activeRequest = useRef(null)
  const nextId = useRef(0)
  const messageEnd = useRef(null)
  const textarea = useRef(null)

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/health', { signal: controller.signal })
      .then(async (response) => {
        const result = await response.json()
        setHealth(response.ok && result.index_ready === true ? 'ready' : 'unavailable')
      })
      .catch((error) => { if (error.name !== 'AbortError') setHealth('unavailable') })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    messageEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [turns])

  useEffect(() => () => activeRequest.current?.abort(), [])

  function updateTurn(id, update) {
    setTurns((current) => current.map((turn) => turn.id === id ? { ...turn, ...update(turn) } : turn))
  }

  async function sendMessage(value) {
    const question = value.trim()
    if (!question || activeRequest.current) return
    const controller = new AbortController()
    activeRequest.current = controller
    const id = ++nextId.current
    const history = historyFor(turns, question)
    setInput('')
    setStreaming(true)
    setTurns((current) => [...current, { id, question, answer: '', sources: [], status: 'streaming', error: '' }])

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: question, history }),
        signal: controller.signal,
      })
      if (!response.ok) {
        throw new Error(response.status === 503
          ? 'The assistant is unavailable. Please check the backend and API settings.'
          : `Unable to send your message (HTTP ${response.status}). Please try again.`)
      }
      await readChatStream(response, (name, data) => {
        if (activeRequest.current !== controller) return
        if (name === 'sources') {
          updateTurn(id, () => ({
            sources: data.sources.filter((source) => typeof source.id === 'string' && safeSourceUrl(source.url)).map((source) => ({
              id: source.id,
              url: source.url,
              title: typeof source.title === 'string' ? source.title : '',
              source: typeof source.source === 'string' ? source.source : '',
            })),
          }))
        } else if (name === 'delta') {
          updateTurn(id, (turn) => ({ answer: turn.answer + data.text }))
        }
      })
      if (activeRequest.current === controller) updateTurn(id, () => ({ status: 'complete' }))
    } catch (error) {
      if (activeRequest.current === controller) {
        const stopped = error.name === 'AbortError'
        updateTurn(id, () => ({
          status: stopped ? 'stopped' : 'error',
          error: stopped ? 'Response stopped.' : error.message || 'Something went wrong. Please try again.',
        }))
      }
    } finally {
      controller.abort()
      if (activeRequest.current === controller) {
        activeRequest.current = null
        setStreaming(false)
      }
    }
  }

  function newChat() {
    activeRequest.current?.abort()
    activeRequest.current = null
    setStreaming(false)
    setTurns([])
    setInput('')
    textarea.current?.focus()
  }

  const healthLabel = health === 'ready' ? 'Assistant ready' : health === 'checking' ? 'Connecting' : 'Backend unavailable'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <Mark />
          <div className="brand-wordmark">DAR<span>GLOBAL</span><small>ASSISTANT</small></div>
        </div>
        <div className="sidebar-rule" />
        <button className="new-chat" type="button" onClick={newChat}><Icon name="plus" size={18} /> New conversation</button>
        <div className="sidebar-label">YOUR SPACE</div>
        <div className="sidebar-current"><span className="current-dot" /> Your conversations <span className="sidebar-count">01</span></div>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <Icon name="sparkle" size={20} />
            <p>A more considered way to discover real estate.</p>
            <span>ASK. EXPLORE. DISCOVER.</span>
          </div>
          <div className="sidebar-footer"><span>ASSESSMENT DEMO</span><span>2026</span></div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="topbar-title"><span className="mobile-mark"><Mark small /></span><span>DarGlobal <span className="topbar-divider">/</span> <strong>AI Assistant</strong></span></div>
          <div className="topbar-actions"><span className={`connection connection--${health}`} role="status"><span />{healthLabel}</span><button className="mobile-new-chat" type="button" onClick={newChat} aria-label="New conversation"><Icon name="plus" /></button></div>
        </header>

        <div className="conversation-scroll">
          {turns.length === 0 ? (
            <section className="welcome" aria-labelledby="welcome-heading">
              <div className="welcome-emblem"><Icon name="sparkle" size={28} /></div>
              <div className="eyebrow"><span /> YOUR PERSONAL REAL ESTATE ASSISTANT <span /></div>
              <h1 id="welcome-heading">A little clarity,<br /><em>wherever you are.</em></h1>
              <p className="welcome-description">Discover projects, explore properties, and find the answers you need. Consider this the beginning of a good conversation.</p>
              <div className="suggestion-heading"><span>NOT SURE WHERE TO START?</span><span>01 — 04</span></div>
              <div className="suggestions">
                {suggestions.map((item, index) => (
                  <button className="suggestion" type="button" key={item.title} onClick={() => sendMessage(item.prompt)} disabled={streaming}>
                    <span className="suggestion-top"><span className="suggestion-icon"><Icon name={item.icon} size={19} /></span><span className="suggestion-number">0{index + 1}</span></span>
                    <span className="suggestion-title">{item.title}</span>
                    <span className="suggestion-link">Ask about this <Icon name="arrow" size={15} /></span>
                  </button>
                ))}
              </div>
            </section>
          ) : (
            <section className="conversation" aria-label="Conversation">
              <div className="conversation-intro"><span className="intro-line" /> A CONVERSATION WITH DARGLOBAL <span className="intro-line" /></div>
              {turns.map((turn) => (
                <div className="turn" key={turn.id}>
                  <div className="user-message"><div className="message-label">YOU</div><div className="user-bubble" dir="auto">{turn.question}</div></div>
                  <div className="assistant-message">
                    <Mark small />
                    <div className="assistant-content">
                      <div className="message-label">DARGLOBAL ASSISTANT <span> · </span> AI</div>
                      {turn.answer && <div className="answer-text" dir="auto">{turn.answer}</div>}
                      {turn.status === 'streaming' && !turn.answer && <div className="thinking" role="status"><span /><span /><span /><span className="thinking-label">Finding an answer</span></div>}
                      {turn.error && <p className={`message-error${turn.status === 'stopped' ? ' message-error--stopped' : ''}`} role="status">{turn.error}</p>}
                      {turn.sources.length > 0 && (
                        <div className="sources">
                          <div className="sources-label">EXPLORE THE SOURCES</div>
                          <div className="source-list">
                            {turn.sources.map((source) => <a key={`${source.id}-${source.url}`} href={source.url} target="_blank" rel="noopener noreferrer"><span>{source.id}</span>{source.title || source.source || 'Source'}<Icon name="link" size={13} /></a>)}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messageEnd} />
            </section>
          )}
        </div>

        <div className="composer-wrap">
          <form className="composer" onSubmit={(event) => { event.preventDefault(); sendMessage(input) }}>
            <label className="sr-only" htmlFor="chat-input">Your message</label>
            <textarea id="chat-input" ref={textarea} rows="1" maxLength={2000} value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                event.preventDefault()
                event.currentTarget.form.requestSubmit()
              }
            }} placeholder="Ask anything about DarGlobal or Wasalt..." dir="auto" />
            {streaming ? (
              <button className="send-button stop-button" type="button" onClick={() => activeRequest.current?.abort()} aria-label="Stop response"><Icon name="stop" size={19} /></button>
            ) : (
              <button className="send-button" type="submit" disabled={!input.trim()} aria-label="Send message"><Icon name="send" size={20} /></button>
            )}
          </form>
          <div className="composer-footer"><span>AI responses may be inaccurate. Property information is a snapshot, not live.</span><span className="keyboard-hint">ENTER TO SEND <kbd>↵</kbd></span></div>
        </div>
      </main>
    </div>
  )
}

export default App
