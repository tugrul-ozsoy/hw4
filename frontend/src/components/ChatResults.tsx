import { useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useChatResults } from '../chatResults.tsx'
import ProductCard from './ProductCard.tsx'

/** Product matches from the latest chat search, rendered on the page (Problem 7). */
export default function ChatResults() {
  const { results, setResults } = useChatResults()
  const { pathname } = useLocation()
  const ref = useRef<HTMLElement>(null)
  // On a single-item page the detail view (large image + full info) comes first, so the grid steps aside.
  // It stays in memory: Back to the previous page shows it again.
  const onDetailPage = pathname.startsWith('/products/')

  useEffect(() => {
    if (results && !onDetailPage) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [results, onDetailPage])

  if (!results || onDetailPage) return null
  const shown = results.products.length

  return (
    <section ref={ref} className="chat-results" aria-live="polite" aria-label={`Chat results: ${results.title}`}>
      <div className="page chat-results-inner">
        <header className="chat-results-header">
          <div>
            <p className="eyebrow">From your chat</p>
            <h2>{results.title}</h2>
            <p className="muted">
              {results.total_matches} {results.total_matches === 1 ? 'match' : 'matches'}
              {shown < results.total_matches && ` · showing ${shown}`}
            </p>
          </div>
          <div className="chat-results-actions">
            {shown < results.total_matches && (
              <Link to="/products" className="btn btn-outline">See all products</Link>
            )}
            <button type="button" className="chat-results-close" onClick={() => setResults(null)}
              aria-label="Hide chat results">
              ×
            </button>
          </div>
        </header>
        <div className="product-grid">
          {results.products.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </div>
    </section>
  )
}
