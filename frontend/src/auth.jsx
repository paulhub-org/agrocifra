import { createContext, useContext, useEffect, useState } from 'react'
import { api, clearToken, setToken } from './api'

const AuthCtx = createContext(null)

export const ROLE_LABELS = {
  organization: 'Организация',
  regional_operator: 'Региональный оператор',
  digitalization_office: 'Офис цифровизации',
  state_authority: 'Государственный орган',
}

export function AuthProvider({ children }) {
  const [token, setTok] = useState(() => localStorage.getItem('agrocifra_token'))
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(token))

  useEffect(() => {
    if (!token) { setUser(null); return }
    setLoading(true)
    api.me()
      .then(setUser)
      .catch(() => { clearToken(); setTok(null); setUser(null) })
      .finally(() => setLoading(false))
  }, [token])

  async function login(username, password) {
    const t = await api.login(username, password)
    setToken(t.access_token)
    setTok(t.access_token)
  }
  function logout() { clearToken(); setTok(null); setUser(null) }

  const roleLabel = user ? (ROLE_LABELS[user.role] || user.role) : ''
  return (
    <AuthCtx.Provider value={{ token, user, loading, login, logout, roleLabel }}>
      {children}
    </AuthCtx.Provider>
  )
}

export const useAuth = () => useContext(AuthCtx)
