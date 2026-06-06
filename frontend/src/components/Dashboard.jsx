import { useEffect, useState } from 'react'
import { api } from '../api.js'

const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null)
const fmt = (x) => (x == null ? '—' : x.toFixed(2).replace('.', ','))

function Tile({ value, label, hint, accent }) {
  return (
    <div className={`tile${accent ? ' accent' : ''}`}>
      <div className="tile-val">{value}</div>
      <div className="tile-lbl">{label}</div>
      {hint && <div className="tile-hint">{hint}</div>}
    </div>
  )
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    Promise.all([api.organizations(), api.efficiencyAssessments(), api.maturityAssessments()])
      .then(([orgs, eff, mat]) => setData({ orgs, eff, mat }))
      .catch((e) => setError(e.message))
  }, [])
  if (error) return <div className="error">{error}</div>
  if (!data) return <div className="muted">Загрузка…</div>

  const meKE = mean(data.eff.map((a) => a.coefficient))
  const meMat = mean(data.mat.map((a) => a.maturity))
  const effOk = data.eff.filter((a) => a.coefficient > 1).length

  return (
    <div className="stagger">
      <h2 className="page-title">Дашборд</h2>
      <div className="tiles">
        <Tile value={data.orgs.length} label="Организаций" />
        <Tile value={data.eff.length} label="Оценок эффективности" />
        <Tile value={fmt(meKE)} label="Среднее КЭц" accent
          hint={meKE == null ? '' : meKE > 1 ? 'в среднем эффективна' : 'на пороге / ниже'} />
        <Tile value={`${effOk} / ${data.eff.length}`} label="Эффективных (КЭц > 1,0)" />
        <Tile value={data.mat.length} label="Оценок зрелости" />
        <Tile value={fmt(meMat)} label="Средняя цифровая зрелость" />
      </div>

      <h3 className="section">Последние оценки эффективности</h3>
      {data.eff.length === 0 ? <p className="muted">Пока нет данных.</p> : (
        <table className="grid">
          <thead><tr><th>Организация</th><th>КЭц</th><th>Зона</th><th>Источник</th></tr></thead>
          <tbody>
            {data.eff.slice(-8).reverse().map((a) => (
              <tr key={a.id}>
                <td>#{a.organization_id}</td>
                <td className="num">{fmt(a.coefficient)}</td>
                <td><span className={`badge ${a.zone === 'эффективна' ? 'ok' : a.zone === 'неэффективна' ? 'bad' : 'mid'}`}>{a.zone}</span></td>
                <td className="muted">{a.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3 className="section">Последние оценки зрелости</h3>
      {data.mat.length === 0 ? <p className="muted">Пока нет данных.</p> : (
        <table className="grid">
          <thead><tr><th>Организация</th><th>Зрелость</th><th>Зона</th><th>Источник</th></tr></thead>
          <tbody>
            {data.mat.slice(-8).reverse().map((a) => (
              <tr key={a.id}>
                <td>#{a.organization_id}</td>
                <td className="num">{fmt(a.maturity)}</td>
                <td><span className={`badge ${a.zone === 'высокая' ? 'ok' : a.zone === 'низкая' ? 'bad' : 'mid'}`}>{a.zone}</span></td>
                <td className="muted">{a.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
