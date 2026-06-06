import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { ROLE_LABELS, useAuth } from '../auth.jsx'

const ROLES = ['organization', 'regional_operator', 'digitalization_office', 'state_authority']

export default function Login() {
  const { login, token } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [regLogin, setRegLogin] = useState('')
  const [regPass, setRegPass] = useState('')
  const [regName, setRegName] = useState('')
  const [regRole, setRegRole] = useState('organization')
  const [okMsg, setOkMsg] = useState('')

  useEffect(() => { if (token) navigate('/', { replace: true }) }, [token, navigate])

  async function submit(e) {
    e.preventDefault(); setError(''); setBusy(true)
    try { await login(username, password); navigate('/') }
    catch (ex) { setError(ex.message || 'Ошибка входа') }
    finally { setBusy(false) }
  }

  async function submitRegister(e) {
    e.preventDefault(); setError(''); setOkMsg(''); setBusy(true)
    try {
      const r = await api.register({
        login: regLogin, password: regPass, role: regRole, full_name: regName || null,
      })
      setOkMsg(r.message || 'Заявка отправлена и ожидает подтверждения.')
      setRegLogin(''); setRegPass(''); setRegName(''); setMode('login')
    } catch (ex) { setError(ex.message || 'Ошибка регистрации') }
    finally { setBusy(false) }
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={mode === 'login' ? submit : submitRegister}>
        <div className="auth-brand"><span className="logo">🌾</span><h1>АгроЦифра</h1></div>
        <p className="muted auth-sub">
          Цифровая зрелость и оценка эффективности цифровизации
          сельскохозяйственных организаций
        </p>

        {mode === 'login' ? (
          <>
            <label>Логин
              <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
            </label>
            <label>Пароль
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </label>
            {okMsg && <div className="notice">{okMsg}</div>}
            {error && <div className="error">{error}</div>}
            <button className="primary" disabled={busy}>{busy ? 'Вход…' : 'Войти'}</button>
            <small className="muted hint">Демо-доступ для UAT: org · region · office · gov (пароли *123)</small>
            <button type="button" className="link-btn" onClick={() => { setMode('register'); setError(''); setOkMsg('') }}>
              Создать учётную запись
            </button>
          </>
        ) : (
          <>
            <label>Логин
              <input value={regLogin} onChange={(e) => setRegLogin(e.target.value)} autoFocus required />
            </label>
            <label>Пароль
              <input type="password" value={regPass} onChange={(e) => setRegPass(e.target.value)} required />
            </label>
            <label>ФИО / наименование
              <input value={regName} onChange={(e) => setRegName(e.target.value)} />
            </label>
            <label>Роль
              <select value={regRole} onChange={(e) => setRegRole(e.target.value)}>
                {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
              </select>
            </label>
            {error && <div className="error">{error}</div>}
            <button className="primary" disabled={busy}>{busy ? 'Отправка…' : 'Отправить заявку'}</button>
            <small className="muted hint">Учётная запись активируется после подтверждения администратором.</small>
            <button type="button" className="link-btn" onClick={() => { setMode('login'); setError('') }}>
              ← Назад ко входу
            </button>
          </>
        )}
      </form>
    </div>
  )
}
