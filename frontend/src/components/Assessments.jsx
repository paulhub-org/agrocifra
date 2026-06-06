import { useEffect, useState } from 'react'
import { api } from '../api.js'

const fmt = (x) => (x == null ? '—' : Number(x).toFixed(2).replace('.', ','))
const badge = (zone) => zone === 'эффективна' || zone === 'высокая' ? 'ok'
  : zone === 'неэффективна' || zone === 'низкая' ? 'bad' : 'mid'

export default function Assessments() {
  const [tab, setTab] = useState('efficiency')
  const [eff, setEff] = useState([])
  const [mat, setMat] = useState([])
  const [orgs, setOrgs] = useState([])
  const [error, setError] = useState('')
  useEffect(() => {
    Promise.all([api.efficiencyAssessments(), api.maturityAssessments(), api.organizations()])
      .then(([e, m, o]) => { setEff(e); setMat(m); setOrgs(o) }).catch((e) => setError(e.message))
  }, [])
  if (error) return <div className="error">{error}</div>
  const orgName = Object.fromEntries(orgs.map((o) => [o.id, o.name]))
  return (
    <div>
      <h2 className="page-title">Оценки</h2>
      <div className="tabs">
        <button className={tab === 'efficiency' ? 'tab active' : 'tab'} onClick={() => setTab('efficiency')}>Эффективность ({eff.length})</button>
        <button className={tab === 'maturity' ? 'tab active' : 'tab'} onClick={() => setTab('maturity')}>Цифровая зрелость ({mat.length})</button>
      </div>
      {tab === 'efficiency' ? (
        <table className="grid">
          <thead><tr><th>Организация</th><th>Эконом.</th><th>Эколог.</th><th>Соц.</th><th>КЭц</th><th>Зона</th><th>Источник</th></tr></thead>
          <tbody>{eff.map((a) => (
            <tr key={a.id}>
              <td>{orgName[a.organization_id] || `#${a.organization_id}`}</td>
              <td className="num">{fmt(a.economic_index)}</td>
              <td className="num">{fmt(a.ecological_index)}</td>
              <td className="num">{fmt(a.social_index)}</td>
              <td className="num strong">{fmt(a.coefficient)}</td>
              <td><span className={`badge ${badge(a.zone)}`}>{a.zone}</span></td>
              <td className="muted">{a.source}</td>
            </tr>))}
          </tbody>
        </table>
      ) : (
        <table className="grid">
          <thead><tr><th>Организация</th><th>Потребность</th><th>Возможности</th><th>Зрелость</th><th>Зона</th><th>Источник</th></tr></thead>
          <tbody>{mat.map((a) => (
            <tr key={a.id}>
              <td>{orgName[a.organization_id] || `#${a.organization_id}`}</td>
              <td className="num">{fmt(a.need_avg)}</td>
              <td className="num">{fmt(a.capability_avg)}</td>
              <td className="num strong">{fmt(a.maturity)}</td>
              <td><span className={`badge ${badge(a.zone)}`}>{a.zone}</span></td>
              <td className="muted">{a.source}</td>
            </tr>))}
          </tbody>
        </table>
      )}
    </div>
  )
}
