import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../auth.tsx'

const MAIN_LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products', end: false },
  { to: '/about', label: 'About Us', end: false },
]

export default function NavBar() {
  const { pathname } = useLocation()
  const { user, loading, logout } = useAuth()
  // The menu is "open on" one path, so it closes by itself on any route change (links, Back/Forward).
  const [openOn, setOpenOn] = useState<string | null>(null)
  const open = openOn === pathname
  const close = () => setOpenOn(null)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpenOn(null)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])
  const linkClass = ({ isActive }: { isActive: boolean }) => (isActive ? 'nav-link active' : 'nav-link')

  return (
    <header className="site-header">
      <div className="announcement">Licensed Yale apparel · Live stock by size · A New Haven shop since 1975</div>
      <nav className="navbar" aria-label="Main">
        <Link to="/" className="brand" onClick={close}>
          <span className="brand-mark" aria-hidden="true">Y</span>
          <span className="brand-text">
            <span className="brand-name">Campus Customs</span>
            <span className="brand-sub">Yale Bulldog Blue</span>
          </span>
        </Link>

        <button
          className="nav-toggle"
          aria-expanded={open}
          aria-controls="nav-menu"
          onClick={() => setOpenOn(open ? null : pathname)}
        >
          <span className="sr-only">Toggle menu</span>
          <span className="bar" />
          <span className="bar" />
          <span className="bar" />
        </button>

        <div id="nav-menu" className={open ? 'nav-menu open' : 'nav-menu'}>
          <ul className="nav-links">
            {MAIN_LINKS.map((l) => (
              <li key={l.to}>
                <NavLink to={l.to} end={l.end} className={linkClass} onClick={close}>
                  {l.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <div className="nav-auth" aria-busy={loading}>
            {user ? (
              <>
                <span className="nav-user">Hi, {user.first_name}</span>
                <button
                  type="button"
                  className="btn btn-light"
                  onClick={() => {
                    close()
                    void logout()
                  }}
                >
                  Log out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" className={linkClass} onClick={close}>
                  Log in
                </NavLink>
                <NavLink to="/signup" className="btn btn-light" onClick={close}>
                  Create account
                </NavLink>
              </>
            )}
          </div>
        </div>
      </nav>
    </header>
  )
}
