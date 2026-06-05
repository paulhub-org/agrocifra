import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth.jsx'

export default function Login() {
  const { login, token } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { if (token) navigate('/', { replace: true }) }, [token, navigate])

  async function submit(e) {
    e.preventDefault()
    setError(''); setBusy(true)
    try { await login(username, password); navigate('/') }
    catch (ex) { setError(ex.message || 'Ошибка входа') }
    finally { setBusy(false) }
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-brand"><span className="logo">🌾</span><h1>АгроЦифра</h1></div>
        <p className="muted auth-sub">
          Цифровая зрелость и оценка эффективности цифровизации
          сельскохозяйственных организаций
        </p>
        <label>Логин
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </label>
        <label>Пароль
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <div className="error">{error}</div>}
        <button className="primary" disabled={busy}>{busy ? 'Вход…' : 'Войти'}</button>
        <small className="muted hint">Демо-доступ для UAT: org · region · office · gov (пароли *123)</small>
      </form>
    </div>
  )
}
