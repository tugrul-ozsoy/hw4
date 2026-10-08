import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchProducts, type ProductSummary } from '../api.ts'
import ProductCard from '../components/ProductCard.tsx'

// Cached for the session so returning from a product page renders the grid immediately.
let catalogueCache: ProductSummary[] | null = null

const CATEGORIES = ['All', 'T-Shirts', 'Crewnecks', 'Hoodies', 'Quarter-Zips', 'Jackets & Fleece', 'Long Sleeve']
const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
const SORTS: Record<string, string> = { name: 'Name A–Z', price_low: 'Price: low to high', price_high: 'Price: high to low' }

export default function Products() {
  const [params, setParams] = useSearchParams()
  const requested = params.get('category') ?? 'All'
  const category = CATEGORIES.includes(requested) ? requested : 'All'

  const [products, setProducts] = useState<ProductSummary[] | null>(catalogueCache)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    fetchProducts()
      .then((data) => {
        catalogueCache = data
        if (!cancelled) setProducts(data)
      })
      .catch(() => !cancelled && setError('We could not load the catalogue. Is the shop server running?'))
    return () => {
      cancelled = true
    }
  }, [])

  // Search, sort and size live in the URL too, so Back and shared links keep the same view.
  const query = params.get('q') ?? ''
  const sort = SORTS[params.get('sort') ?? ''] ? (params.get('sort') as string) : 'name'
  const size = SIZES.includes(params.get('size') ?? '') ? (params.get('size') as string) : ''

  function setParam(key: string, value: string) {
    // Functional update: build on the latest URL, so quick successive changes never overwrite each other.
    setParams((prev) => {
      const next = new URLSearchParams(prev)
      if (value && !(key === 'category' && value === 'All') && !(key === 'sort' && value === 'name')) next.set(key, value)
      else next.delete(key)
      return next
    }, { replace: true })
  }
  const choose = (c: string) => setParam('category', c)

  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  const shown = (products ?? [])
    .filter((p) => category === 'All' || p.category === category)
    .filter((p) => !size || p.sizes_in_stock.includes(size))
    .filter((p) => {
      const text = `${p.name} ${p.category} ${p.garment_type} ${p.short_description ?? ''}`.toLowerCase()
      return words.every((w) => text.includes(w))
    })
    .sort((a, b) =>
      sort === 'price_low' ? a.price - b.price || a.name.localeCompare(b.name)
        : sort === 'price_high' ? b.price - a.price || a.name.localeCompare(b.name)
          : a.name.localeCompare(b.name))
  const filtered = Boolean(query || size || category !== 'All')

  return (
    <section className="page">
      <header className="page-header">
        <p className="eyebrow">Shop</p>
        <h1>Products</h1>
        <p className="lead">
          Tees, long sleeves, crewnecks, hoodies, quarter-zips, fleece and jackets for the residential colleges, the
          schools, Bulldog teams and proud Yale families.
        </p>
      </header>

      <div className="chip-row" role="group" aria-label="Product categories">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            type="button"
            aria-pressed={category === c}
            className={category === c ? 'chip active' : 'chip'}
            onClick={() => choose(c)}
          >
            {c}
          </button>
        ))}
      </div>

      <div className="toolbar">
        <label className="toolbar-search">
          <span className="sr-only">Search products</span>
          <input
            type="search"
            value={query}
            onChange={(e) => setParam('q', e.target.value)}
            placeholder="Search: Saybrook, hockey, bulldog, navy…"
          />
        </label>
        <label className="toolbar-select">
          <span>In stock in</span>
          <select value={size} onChange={(e) => setParam('size', e.target.value)}>
            <option value="">Any size</option>
            {SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="toolbar-select">
          <span>Sort</span>
          <select value={sort} onChange={(e) => setParam('sort', e.target.value)}>
            {Object.entries(SORTS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
          </select>
        </label>
      </div>

      {error && (
        <div className="empty-state" role="alert">
          <h2>Catalogue unavailable</h2>
          <p className="muted">{error}</p>
        </div>
      )}

      {!error && products === null && (
        <div className="product-grid" aria-busy="true" aria-label="Loading products">
          {Array.from({ length: 8 }, (_, i) => (
            <div key={i} className="product-card skeleton" />
          ))}
        </div>
      )}

      {products && (
        <>
          <p className="result-count" aria-live="polite">
            {shown.length} {shown.length === 1 ? 'product' : 'products'}
            {category !== 'All' && ` in ${category}`}
            {size && ` with ${size} in stock`}
            {query && ` matching “${query}”`}
            {filtered && (
              <button type="button" className="link-button" onClick={() => setParams({}, { replace: true })}>
                Clear filters
              </button>
            )}
          </p>
          {shown.length === 0 && (
            <div className="empty-state">
              <h2>No matches</h2>
              <p className="muted">Try another word or size, or ask the shop assistant in the chat.</p>
            </div>
          )}
          <div className="product-grid">
            {shown.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
        </>
      )}
    </section>
  )
}
