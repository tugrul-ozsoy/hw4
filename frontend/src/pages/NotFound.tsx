import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <section className="page narrow center">
      <p className="eyebrow">404</p>
      <h1>This page wandered off campus</h1>
      <p className="lead">The link may be old, or the page may have moved.</p>
      <Link to="/" className="btn btn-primary">Back to Home</Link>
    </section>
  )
}
