import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function Organizations() {
  const [orgs, setOrgs] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { api.organizations().then(setOrgs).catch((e) => setError(e.message)) }, [])
  if (error) return <div className="error">{error}</div>
  if (!orgs) return <div className="muted">Загрузка…</div>
  return (
    <div>
      <h2 className="page-title">Организации</h2>
      {orgs.length === 0 ? <p className="muted">Список пуст. Импортируйте данные или введите вручную.</p> : (
        <table className="grid">
          <thead><tr><th>#</th><th>Наименование</th></tr></thead>
          <tbody>{orgs.map((o) => <tr key={o.id}><td className="muted">{o.id}</td><td>{o.name}</td></tr>)}</tbody>
        </table>
      )}
    </div>
  )
}
