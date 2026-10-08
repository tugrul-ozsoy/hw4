import { Link } from 'react-router-dom'
import type { User } from '../api.ts'
import { useAuth } from '../auth.tsx'

/** Shown on Log in / Create account when the shopper is already signed in. */
export default function SignedInCard({ user }: { user: User }) {
  const { logout } = useAuth()
  return (
    <section className="page auth-page">
      <div className="auth-card center">
        <p className="eyebrow">Signed in</p>
        <h1>Hi, {user.first_name}!</h1>
        <p className="muted">You're logged in as {user.email}.</p>
        <div className="signed-in-actions">
          <Link to="/products" className="btn btn-primary">Browse products</Link>
          <button type="button" className="btn btn-outline" onClick={() => void logout()}>Log out</button>
        </div>
      </div>
    </section>
  )
}
