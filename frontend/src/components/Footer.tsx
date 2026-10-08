import { Link } from 'react-router-dom'

const YEAR = new Date().getFullYear()

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <p className="footer-name">Campus Customs</p>
          <p className="muted">
            The New Haven shop behind Yale Bulldog Blue, in business since 1975. Printing and stitching licensed
            Yale apparel.
          </p>
        </div>
        <nav className="footer-col" aria-label="Footer">
          <h2>Shop</h2>
          <Link to="/">Home</Link>
          <Link to="/products">Products</Link>
          <Link to="/about">About Us</Link>
        </nav>
        <nav className="footer-col" aria-label="Account">
          <h2>Account</h2>
          <Link to="/login">Log in</Link>
          <Link to="/signup">Create account</Link>
        </nav>
        <div className="footer-col">
          <h2>Visit</h2>
          <p>57 Broadway</p>
          <p>New Haven, CT 06511</p>
          <a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a>
        </div>
      </div>
      <p className="footer-legal">© {YEAR} Campus Customs · Yale Bulldog Blue</p>
    </footer>
  )
}
