import { Link } from 'react-router-dom'
import { displayName, formatPrice, type CardProduct } from '../api.ts'
import ProductImage from './ProductImage.tsx'

export default function ProductCard({ product }: { product: CardProduct }) {
  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <ProductImage className="product-image" src={product.image_url} alt="" />
      <div className="product-body">
        <p className="product-category">{product.category}</p>
        <h2 className="product-name">{displayName(product.name)}</h2>
        <p className="product-desc">{product.short_description ?? 'No written description yet.'}</p>
        <p className="product-price">{formatPrice(product.price)}</p>
      </div>
    </Link>
  )
}
