import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import Markdown from 'react-markdown'
import { Link, useLocation } from 'react-router-dom'
import { ApiError, fetchChatHistory, formatPrice, sendChatMessage, type ChatMessage } from '../api.ts'
import { useAuth } from '../auth.tsx'
import { useChatResults } from '../chatResults.tsx'

const GREETING: ChatMessage = {
  role: 'assistant',
  content: "Hi! I'm the Campus Customs shop assistant. Ask me about products, prices or sizes.",
}

const SUGGESTIONS = ['What hoodies do you have?', 'Is the Basic Hoodie in stock in L?', 'Anything for Saybrook?']
// On a product page the quick questions are about that item ("this" = the page's product).
const PRODUCT_SUGGESTIONS = ['Is this in stock in M?', 'What colors does it come in?', 'Show me something similar']

export default function ChatWidget() {
  const { user } = useAuth()
  const { setResults } = useChatResults()
  const { pathname } = useLocation()
  const currentProductId = pathname.startsWith('/products/') ? decodeURIComponent(pathname.slice(10)) : null
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const launcherRef = useRef<HTMLButtonElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  // Problem 8: logged-in shoppers get their saved chat back; logging out starts a fresh guest chat.
  const userId = user?.id ?? null
  useEffect(() => {
    let cancelled = false
    const saved = userId === null ? Promise.resolve([]) : fetchChatHistory()
    saved.then((history) => {
      if (!cancelled) setMessages([GREETING, ...history])
    })
    return () => {
      cancelled = true
    }
  }, [userId])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  // "Ask about this item" on a product page opens the chat.
  useEffect(() => {
    const openChat = () => setOpen(true)
    window.addEventListener('cc:open-chat', openChat)
    return () => window.removeEventListener('cc:open-chat', openChat)
  }, [])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  }, [messages, sending])

  function close() {
    setOpen(false)
    launcherRef.current?.focus()
  }

  async function send(text: string) {
    const content = text.trim()
    if (!content || sending) return
    // Earlier turns only: the agent should not see the UI greeting or this message twice.
    const prior = messages.filter((m) => m !== GREETING)
    setMessages([...messages, { role: 'user', content }])
    setDraft('')
    setSending(true)
    try {
      const { reply, products, results } = await sendChatMessage(content, prior, currentProductId)
      setMessages((m) => [...m, { role: 'assistant', content: reply, products }])
      if (results && results.products.length > 0) setResults(results)  // show matches on the page
    } catch (err) {
      const text = err instanceof ApiError ? err.message : 'Sorry, something went wrong. Please try again.'
      setMessages((m) => [...m, { role: 'assistant', content: text }])
    } finally {
      setSending(false)
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    void send(draft)
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void send(draft)
    }
  }

  return (
    <div className="chat-root" onKeyDown={(e) => e.key === 'Escape' && open && close()}>
      {open && (
        <section id="chat-panel" className="chat-panel" role="dialog" aria-label="Shop assistant chat">
          <header className="chat-header">
            <div>
              <p className="chat-title">Shop assistant</p>
              <p className="chat-sub">
                {user ? `Hi ${user.first_name}! Your chat is saved.` : 'Guest chat (log in to save it)'}
              </p>
            </div>
            <button className="chat-close" onClick={close} aria-label="Close chat">
              ×
            </button>
          </header>

          <div className="chat-messages" ref={listRef} aria-live="polite">
            {messages.map((m, i) => (
              <div key={i} className={`chat-turn ${m.role}`}>
                <div className={`chat-bubble ${m.role}`}>
                  {m.role === 'assistant' ? <Markdown>{m.content}</Markdown> : m.content}
                </div>
                {m.products && m.products.length > 0 && (
                  <div className="chat-cards">
                    {m.products.map((p) => (
                      <Link key={p.product_id} to={`/products/${p.product_id}`} className="chat-card">
                        <img src={p.image_url} alt="" />
                        <span className="chat-card-name">{p.name}</span>
                        <span className="chat-card-price">{formatPrice(p.price)}</span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {sending && (
              <div className="chat-bubble assistant typing">
                <span className="sr-only">Assistant is typing</span>
                <span className="dot" aria-hidden="true" />
                <span className="dot" aria-hidden="true" />
                <span className="dot" aria-hidden="true" />
              </div>
            )}
          </div>

          {(messages.length === 1 || currentProductId) && !sending && (
            <div className="chat-suggestions">
              {(currentProductId ? PRODUCT_SUGGESTIONS : SUGGESTIONS).map((s) => (
                <button key={s} type="button" className="chip small" onClick={() => void send(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}

          <form className="chat-input" onSubmit={handleSubmit}>
            <textarea
              ref={inputRef}
              rows={1}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about a product…"
              aria-label="Message"
            />
            <button type="submit" className="btn btn-primary" disabled={!draft.trim() || sending}>
              Send
            </button>
          </form>
        </section>
      )}

      <button
        ref={launcherRef}
        className="chat-launcher"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls="chat-panel"
        aria-label={open ? 'Close shop assistant' : 'Open shop assistant'}
      >
        {open ? (
          <span className="chat-launcher-x" aria-hidden="true">×</span>
        ) : (
          <>
            <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
              <path
                fill="currentColor"
                fillRule="evenodd"
                d="M6 4h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H9l-5 4V6a2 2 0 0 1 2-2Zm2 5.5v2h2v-2H8Zm3 0v2h2v-2h-2Zm3 0v2h2v-2h-2Z"
              />
            </svg>
            <span>Ask us</span>
          </>
        )}
      </button>
    </div>
  )
}
