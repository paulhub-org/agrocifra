import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { ROLE_LABELS } from '../auth.jsx'

export default function PendingUsers() {
  const [list, setList] = useState(null)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')

  function load() { api.pendingUsers().then(setList).catch((e) => setError(e.message)) }
  useEffect(() => { load() }, [])

  async function approve(id) {
    setMsg('')
    try { await api.activateUser(id); setMsg('Учётная запись подтверждена.'); load() }
    catch (e) { setError(e.message) }
  }

  if (error) return <div className="error">{error}</div>
  if (!list) return <div className="muted">Загрузка…</div>

  return (
    <div>
      <h2 className="page-title">Заявки на регистрацию</h2>
      <p className="muted">Новые учётные записи активируются только после подтверждения.</p>
      {msg && <div className="notice">{msg}</div>}
      {list.length === 0 ? <p className="muted">Нет заявок, ожидающих подтверждения.</p> : (
        <table className="grid">
          <thead><tr><th>Логин</th><th>ФИО / наименование</th><th>Роль</th><th></th></tr></thead>
          <tbody>
            {list.map((u) => (
              <tr key={u.id}>
                <td>{u.login}</td>
                <td>{u.full_name || '—'}</td>
                <td>{ROLE_LABELS[u.role] || u.role}</td>
                <td><button className="primary" onClick={() => approve(u.id)}>Подтвердить</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
