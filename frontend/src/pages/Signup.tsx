import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../api.ts'
import { useAuth } from '../auth.tsx'
import SignedInCard from '../components/SignedInCard.tsx'

const MIN_PASSWORD = 8

export default function Signup() {
  const { user, signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ firstName: '', lastName: '', email: '', password: '', confirm: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user && !submitting) return <SignedInCard user={user} />

  const update = (key: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value })

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    // Quick checks here; the server re-checks everything (length, common passwords, email format).
    if (form.password.length < MIN_PASSWORD) {
      setError(`Password must be at least ${MIN_PASSWORD} characters.`)
      return
    }
    if (form.password !== form.confirm) {
      setError('Passwords do not match.')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      await signup({
        first_name: form.firstName,
        last_name: form.lastName,
        email: form.email,
        password: form.password,
        confirm_password: form.confirm,
      })
      navigate('/products', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the shop server. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="page auth-page">
      <div className="auth-card">
        <p className="eyebrow">Join the Bulldog crew</p>
        <h1>Create account</h1>
        <p className="muted">Save your chats with our shop assistant and get help finding the right fit.</p>

        <form className="form" onSubmit={handleSubmit}>
          <div className="field-row">
            <label className="field">
              <span>First name</span>
              <input autoComplete="given-name" required maxLength={50} value={form.firstName}
                onChange={update('firstName')} />
            </label>
            <label className="field">
              <span>Last name</span>
              <input autoComplete="family-name" required maxLength={50} value={form.lastName}
                onChange={update('lastName')} />
            </label>
          </div>
          <label className="field">
            <span>Email</span>
            <input type="email" autoComplete="email" required value={form.email} onChange={update('email')}
              placeholder="you@yale.edu" />
          </label>
          <label className="field">
            <span>Password</span>
            <div className="password-input">
              <input type={showPassword ? 'text' : 'password'} autoComplete="new-password" required
                minLength={MIN_PASSWORD} maxLength={128} value={form.password} onChange={update('password')} />
              <button type="button" className="show-toggle" onClick={() => setShowPassword(!showPassword)}
                aria-pressed={showPassword}>
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
            <small className="hint">At least {MIN_PASSWORD} characters. A short phrase works well.</small>
          </label>
          <label className="field">
            <span>Confirm password</span>
            <input type={showPassword ? 'text' : 'password'} autoComplete="new-password" required
              value={form.confirm} onChange={update('confirm')} />
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </div>
    </section>
  )
}
