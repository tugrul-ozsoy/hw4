import { createContext, useContext, useState, type ReactNode } from 'react'
import type { ProductResults } from './api.ts'

/** The latest product matches from the chat, shown as a card grid on whatever page is open. */
interface ChatResultsState {
  results: ProductResults | null
  setResults: (results: ProductResults | null) => void
}

const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ProductResults | null>(null)
  return <ChatResultsContext.Provider value={{ results, setResults }}>{children}</ChatResultsContext.Provider>
}

export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
