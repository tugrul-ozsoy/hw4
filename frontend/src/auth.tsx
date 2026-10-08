import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import * as api from './api.ts'

interface AuthState {
  user: api.User | null
  loading: boolean
  signup: (input: api.SignupInput) => Promise<api.User>
  login: (email: string, password: string) => Promise<api.User>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<api.User | null>(null)
  const [loading, setLoading] = useState(true)

  // Restore the session from the HttpOnly cookie on first load.
  useEffect(() => {
    api
      .fetchCurrentUser()
      .then(setUser)
      .finally(() => setLoading(false))
  }, [])

  const signup = useCallback(async (input: api.SignupInput) => {
    const u = await api.signup(input)
    setUser(u)
    return u
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const u = await api.login(email, password)
    setUser(u)
    return u
  }, [])

  const logout = useCallback(async () => {
    await api.logout()
    setUser(null)
  }, [])

  return <AuthContext.Provider value={{ user, loading, signup, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
