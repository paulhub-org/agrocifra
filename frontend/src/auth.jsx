import { createContext, useContext, useEffect, useState } from 'react'
import { api, clearToken, getToken, setToken } from './api'

const AuthCtx = createContext(null)

export const ROLE_LABELS = {
  organization: 'Организация',
  regional_operator: 'Региональный оператор',
  district_operator: 'Районный оператор',
  digitalization_office: 'Офис цифровизации',
  state_authority: 'Государственный орган',
}

export function AuthProvider({ children }) {
  const [token, setTok] = useState(() => localStorage.getItem('agrocifra_token'))
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(token))
  const BASE_KEY = 'agrocifra_base_token'
  const [previewing, setPreviewing] = useState(() => Boolean(sessionStorage.getItem(BASE_KEY)))

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
  function logout() {
    sessionStorage.removeItem(BASE_KEY)
    setPreviewing(false)
    clearToken(); setTok(null); setUser(null)
  }

  async function switchRole(role) {
    const current = getToken()
    if (current && !sessionStorage.getItem(BASE_KEY)) sessionStorage.setItem(BASE_KEY, current)
    const t = await api.switchRole(role)
    setToken(t.access_token); setTok(t.access_token); setPreviewing(true)
  }

  function restoreRole() {
    const base = sessionStorage.getItem(BASE_KEY)
    if (!base) return
    sessionStorage.removeItem(BASE_KEY)
    setToken(base); setTok(base); setPreviewing(false)
  }

  const roleLabel = user ? (ROLE_LABELS[user.role] || user.role) : ''
  return (
    <AuthCtx.Provider value={{ token, user, loading, login, logout, roleLabel, previewing, switchRole, restoreRole }}>
      {children}
    </AuthCtx.Provider>
  )
}

export const useAuth = () => useContext(AuthCtx)
