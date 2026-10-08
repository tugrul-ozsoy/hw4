import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { displayName, fetchProducts, formatPrice, type ProductSummary } from '../api.ts'
import ProductImage from '../components/ProductImage.tsx'

const CATEGORIES = [
  { name: 'T-Shirts', blurb: 'Move-in day to finals week' },
  { name: 'Crewnecks', blurb: 'Crisp walks across Old Campus' },
  { name: 'Hoodies', blurb: 'Late nights at the library' },
  { name: 'Quarter-Zips', blurb: 'Class-ready, game-ready' },
  { name: 'Jackets & Fleece', blurb: 'New England wind, handled' },
]

const CORNERS = [
  { label: 'Saybrook', q: 'saybrook' },
  { label: 'Berkeley', q: 'berkeley' },
  { label: 'Branford', q: 'branford' },
  { label: 'Law School', q: 'law' },
  { label: 'Hockey', q: 'hockey' },
  { label: 'Crew', q: 'crew' },
  { label: 'Sailing', q: 'sailing' },
  { label: 'Bulldogs', q: 'bulldog' },
]

const FEATURED_ID = 'basic-hoodie-big-yale'

export default function Home() {
  const [products, setProducts] = useState<ProductSummary[]>([])

  useEffect(() => {
    let cancelled = false
    fetchProducts()
      .then((data) => !cancelled && setProducts(data))
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  const featured = products.find((p) => p.product_id === FEATURED_ID)
  const coverFor = (category: string) => products.find((p) => p.category === category)
  const openChat = () => window.dispatchEvent(new CustomEvent('cc:open-chat'))

  return (
    <section className="page bento-page">
      <div className="bento">
        {/* Hero */}
        <div className="tile tile-hero">
          <div className="hero-glow" aria-hidden="true" />
          <p className="eyebrow light">Yale Bulldog Blue · by Campus Customs</p>
          <h1>Wear your Yale pride, from Old Campus to the Bowl.</h1>
          <p className="hero-lead">
            From a first-year&apos;s first tee to a reunion-weekend quarter-zip, it&apos;s all licensed Yale gear,
            made by a New Haven shop that has been at it since 1975.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn btn-light">Shop the collection</Link>
            <button type="button" className="btn btn-glass" onClick={openChat}>Ask our assistant</button>
          </div>
          <ul className="hero-pills" aria-label="Why shop with us">
            <li>Officially licensed</li>
            <li>Live stock by size</li>
            <li>57 Broadway, New Haven</li>
          </ul>
        </div>

        {/* Stat */}
        <div className="tile tile-stat">
          <span className="stat-number">1975</span>
          <span className="stat-label">Dressing Yale in navy and white for half a century</span>
        </div>

        {/* Featured product */}
        <Link to={`/products/${FEATURED_ID}`} className="tile tile-featured">
          <span className="tile-tag">Shop favorite</span>
          {featured && <ProductImage className="tile-photo" src={featured.image_url} alt="" lazy={false} />}
          <div className="tile-caption">
            <strong>{featured ? displayName(featured.name) : 'Basic Hoodie Big Yale'}</strong>
            {featured && <span>{formatPrice(featured.price)}</span>}
          </div>
        </Link>

        {/* Assistant */}
        <button type="button" className="tile tile-assistant" onClick={openChat}>
          <span className="assistant-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="26" height="26">
              <path fill="currentColor" fillRule="evenodd"
                d="M6 4h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H9l-5 4V6a2 2 0 0 1 2-2Zm2 5.5v2h2v-2H8Zm3 0v2h2v-2h-2Zm3 0v2h2v-2h-2Z" />
            </svg>
          </span>
          <strong>Ask the shop assistant</strong>
          <span>Live prices, sizes in stock and picks for your college, all in one chat.</span>
        </button>

        {/* Categories with real product photos */}
        {CATEGORIES.map((c, i) => {
          const cover = coverFor(c.name)
          return (
            <Link key={c.name} to={`/products?category=${encodeURIComponent(c.name)}`}
              className={`tile tile-category tile-c${i}`}>
              {cover && <ProductImage className="tile-photo" src={cover.image_url} alt="" lazy={false} />}
              <div className="tile-caption">
                <strong>{c.name}</strong>
                <span>{c.blurb}</span>
              </div>
            </Link>
          )
        })}

        {/* Rep your corner */}
        <div className="tile tile-corners">
          <h2>Rep your corner of Yale</h2>
          <p>Residential colleges, schools and Bulldog teams. Chances are we have something with its name on it.</p>
          <div className="corner-chips">
            {CORNERS.map((c) => (
              <Link key={c.q} to={`/products?q=${encodeURIComponent(c.q)}`} className="glass-chip">{c.label}</Link>
            ))}
          </div>
        </div>

        {/* Visit */}
        <div className="tile tile-visit">
          <p className="eyebrow">Visit the shop</p>
          <h2>57 Broadway, New Haven</h2>
          <p>Try on sizes, find a gift for the family, or just say hi on your way to class.</p>
          <Link to="/about" className="btn btn-primary">Our story</Link>
        </div>
      </div>
    </section>
  )
}
