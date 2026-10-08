import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { displayName, fetchProduct, formatPrice, type ProductDetail as Product, type SizeStock } from '../api.ts'
import ProductImage from '../components/ProductImage.tsx'

const STATUS_LABEL = {
  in_stock: (s: SizeStock) => `${s.quantity} in stock`,
  low_stock: (s: SizeStock) => `Only ${s.quantity} left`,
  sold_out: () => 'Sold out',
}

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const [result, setResult] = useState<{ id: string; product?: Product; error?: string } | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchProduct(productId)
      .then((product) => !cancelled && setResult({ id: productId, product }))
      .catch((e: Error) =>
        !cancelled &&
        setResult({
          id: productId,
          error: e.message === 'not_found' ? 'not_found' : 'We could not load this product. Is the shop server running?',
        }),
      )
    return () => {
      cancelled = true
    }
  }, [productId])

  const current = result?.id === productId ? result : null
  const product = current?.product

  useEffect(() => {
    if (product) document.title = `${product.name} | Campus Customs`
    else if (current?.error === 'not_found') document.title = 'Product not found | Campus Customs'
    else if (current?.error) document.title = 'Something went wrong | Campus Customs'
    else document.title = 'Loading product… | Campus Customs'
  }, [product, current])

  if (!current) {
    return (
      <section className="page">
        <div className="detail-layout" aria-busy="true">
          <div className="detail-image skeleton" />
          <div className="skeleton detail-skeleton-text" />
        </div>
      </section>
    )
  }

  if (current.error) {
    return (
      <section className="page narrow center">
        <p className="eyebrow">{current.error === 'not_found' ? '404' : 'Error'}</p>
        <h1>{current.error === 'not_found' ? "We couldn't find that item" : 'Something went wrong'}</h1>
        <p className="lead">
          {current.error === 'not_found' ? 'It may have been renamed or removed from the catalogue.' : current.error}
        </p>
        <Link to="/products" className="btn btn-primary">Back to Products</Link>
      </section>
    )
  }

  const p = product!
  const soldOut = p.inventory.filter((s) => s.status === 'sold_out').map((s) => s.size)

  return (
    <section className="page">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/products">Products</Link>
        <span aria-hidden="true">/</span>
        <Link to={`/products?category=${encodeURIComponent(p.category)}`}>{p.category}</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{p.name}</span>
      </nav>

      <div className="detail-layout">
        <ProductImage className="detail-image" src={p.image_url} alt={p.name} lazy={false} />

        <div className="detail-info">
          <p className="eyebrow">{p.category}</p>
          <h1>{displayName(p.name)}</h1>
          <p className="detail-price">{formatPrice(p.price)}</p>
          <p className="muted small">Same price for every size.</p>

          <div className="detail-section">
            <h2>Description</h2>
            <p>{p.description ??
                "We don't have a written description for this item yet. The photo shows the design, and the price and sizes below are current."}</p>
          </div>

          <dl className="detail-facts">
            <div>
              <dt>Style</dt>
              <dd className="capitalize">{p.garment_type}</dd>
            </div>
            {p.garment_color && (
              <div>
                <dt>Garment color</dt>
                <dd className="capitalize">{p.garment_color}</dd>
              </div>
            )}
            {p.design_colors.length > 0 && (
              <div>
                <dt>Print &amp; trim colors</dt>
                <dd className="capitalize">{p.design_colors.join(', ')}</dd>
              </div>
            )}
          </dl>

          <div className="detail-section">
            <h2>Sizes &amp; stock</h2>
            <ul className="size-grid">
              {p.inventory.map((s) => (
                <li key={s.size} className={`size-box ${s.status}`}>
                  <span className="size-label">{s.size}</span>
                  <span className="size-status">{STATUS_LABEL[s.status](s)}</span>
                </li>
              ))}
            </ul>
            <p className="muted small">
              {p.total_stock} units available across all sizes
              {soldOut.length > 0 && `. Sold out in ${soldOut.join(', ')}, so those sizes can't be ordered right now`}.
            </p>
          </div>

          <div className="detail-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => window.dispatchEvent(new CustomEvent('cc:open-chat'))}
            >
              Ask about this item
            </button>
            <Link to="/products" className="btn btn-outline">← Back to all products</Link>
          </div>
        </div>
      </div>
    </section>
  )
}
