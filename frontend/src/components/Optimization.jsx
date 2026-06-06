import { useState } from 'react'
import Plotly from 'plotly.js-basic-dist-min'
import createPlotlyComponent from 'react-plotly.js/factory'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'

const Plot = createPlotlyComponent(Plotly)
const num = (v) => Number(String(v).replace(',', '.')) || 0
const money = (x) => Number(x).toLocaleString('ru-RU')

// Стартовый пример: 7 пилотных организаций (КЭц — фактические; capex/эффект — иллюстративные)
const SEED = [
  { name: 'Шипяны-АСК', cost: 1200000, effect: 2100000, var_type: 'continuous', score: 1.19, maturity: 0.36, credit_limit: '' },
  { name: 'Достоево', cost: 900000, effect: 1300000, var_type: 'binary', score: 1.21, maturity: 0.20, credit_limit: '' },
  { name: 'ДолжаАгро', cost: 800000, effect: 600000, var_type: 'continuous', score: 0.56, maturity: 0.55, credit_limit: '' },
  { name: 'Криничная', cost: 1000000, effect: 1500000, var_type: 'continuous', score: 1.06, maturity: 0.39, credit_limit: 500000 },
  { name: 'Олекшицы', cost: 700000, effect: 720000, var_type: 'continuous', score: 1.00, maturity: 0.23, credit_limit: '' },
  { name: 'Минскоблагросервис', cost: 850000, effect: 780000, var_type: 'continuous', score: 0.90, maturity: 0.46, credit_limit: '' },
  { name: 'Учхоз БГСХА', cost: 950000, effect: 1350000, var_type: 'continuous', score: 1.08, maturity: 0.26, credit_limit: '' },
]

function PortfolioOptimization() {
  const [budget, setBudget] = useState(4000000)
  const [coverageWeight, setCoverageWeight] = useState(0)
  const [threshold, setThreshold] = useState(1.0)
  const [rows, setRows] = useState(SEED)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [impName, setImpName] = useState('')
  const [impMsg, setImpMsg] = useState('')
  const [impBusy, setImpBusy] = useState(false)

  const setRow = (i, k, v) => setRows((rs) => rs.map((r, j) => (j === i ? { ...r, [k]: v } : r)))
  const addRow = () => setRows((rs) => [...rs, { name: '', cost: 0, effect: 0, var_type: 'continuous', score: 0, maturity: 0, credit_limit: '' }])
  const delRow = (i) => setRows((rs) => rs.filter((_, j) => j !== i))

  async function importModel(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    if (!impName.trim()) { setImpMsg('Укажите наименование организации перед загрузкой'); return }
    setImpMsg(''); setImpBusy(true)
    try {
      const r = await api.importModel(file, impName.trim())
      setRows((rs) => [...rs, {
        name: r.organization, cost: r.cost, effect: r.effect,
        var_type: 'continuous', score: 0, maturity: 0,
        credit_limit: r.credit_limit == null ? '' : r.credit_limit,
      }])
      setImpMsg(`Загружено: ${r.organization} — стоимость ${money(r.cost)}, эффект ${money(r.effect)}` +
        (r.credit_limit == null ? '' : `, кредитный предел ${money(r.credit_limit)}`))
      setImpName('')
    } catch (ex) { setImpMsg(ex.message) } finally { setImpBusy(false) }
  }

  async function run() {
    setError(''); setResult(null); setBusy(true)
    try {
      const projects = rows.filter((r) => r.name && num(r.cost) > 0).map((r) => ({
        name: r.name, cost: num(r.cost), effect: num(r.effect),
        var_type: r.var_type, score: num(r.score), maturity: num(r.maturity),
        credit_limit: r.credit_limit === '' || r.credit_limit == null ? null : num(r.credit_limit),
      }))
      const res = await api.optimize({
        budget: num(budget), coverage_weight: num(coverageWeight),
        threshold: num(threshold), projects,
      })
      setResult(res)
    } catch (ex) { setError(ex.message) } finally { setBusy(false) }
  }

  const allocs = result?.allocations ?? []

  return (
    <div>
      <h2 className="page-title">Оптимизация затрат на цифровизацию</h2>
      <p className="muted">
        Комбинированный подход: отбор организаций и объём финансирования в пределах
        кредитоспособности; максимизация суммарного эффекта при бюджетном ограничении
        с учётом охвата организаций выше порога. Решатель — PuLP/CBC.
      </p>

      <div className="form-grid" style={{ marginBottom: 12 }}>
        <label>Бюджет, руб.
          <input inputMode="decimal" value={budget} onChange={(e) => setBudget(e.target.value)} />
        </label>
        <label>Порог (КЭц/зрелость)
          <input inputMode="decimal" value={threshold} onChange={(e) => setThreshold(e.target.value)} />
        </label>
        <label>Вес охвата (вторичная цель)
          <input inputMode="decimal" value={coverageWeight} onChange={(e) => setCoverageWeight(e.target.value)} />
        </label>
      </div>

      <div className="card" style={{ padding: '12px 14px', marginBottom: 12 }}>
        <div className="muted" style={{ fontSize: 13, marginBottom: 6 }}>
          Импорт из Excel-модели «Оценка проекта и долгового риска»: стоимость (CAPEX),
          эффект (NPV) и кредитный предел (по запасу DSCR) подставляются автоматически.
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <input placeholder="Наименование организации" value={impName}
            onChange={(e) => setImpName(e.target.value)} style={{ minWidth: 240 }} />
          <label className="ghost" style={{ cursor: 'pointer' }}>
            {impBusy ? 'Загрузка…' : 'Загрузить модель (.xlsx)'}
            <input type="file" accept=".xlsx,.xlsm" onChange={importModel}
              disabled={impBusy} style={{ display: 'none' }} />
          </label>
        </div>
        {impMsg && <div className="muted" style={{ fontSize: 13, marginTop: 6 }}>{impMsg}</div>}
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table className="opt-table" style={tableStyle}>
          <thead>
            <tr>
              {['Организация', 'Стоимость', 'Эффект', 'Тип', 'КЭц', 'Зрелость', 'Кредитный предел', ''].map((h) => (
                <th key={h} style={thStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td style={tdStyle}><input style={cell} value={r.name} onChange={(e) => setRow(i, 'name', e.target.value)} /></td>
                <td style={tdStyle}><input style={cellNum} inputMode="decimal" value={r.cost} onChange={(e) => setRow(i, 'cost', e.target.value)} /></td>
                <td style={tdStyle}><input style={cellNum} inputMode="decimal" value={r.effect} onChange={(e) => setRow(i, 'effect', e.target.value)} /></td>
                <td style={tdStyle}>
                  <select value={r.var_type} onChange={(e) => setRow(i, 'var_type', e.target.value)}>
                    <option value="continuous">масштаб.</option>
                    <option value="binary">всё/ничего</option>
                  </select>
                </td>
                <td style={tdStyle}><input style={cellNum} inputMode="decimal" value={r.score} onChange={(e) => setRow(i, 'score', e.target.value)} /></td>
                <td style={tdStyle}><input style={cellNum} inputMode="decimal" value={r.maturity} onChange={(e) => setRow(i, 'maturity', e.target.value)} /></td>
                <td style={tdStyle}><input style={cellNum} inputMode="decimal" placeholder="—" value={r.credit_limit} onChange={(e) => setRow(i, 'credit_limit', e.target.value)} /></td>
                <td style={tdStyle}><button className="ghost" onClick={() => delRow(i)}>✕</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ display: 'flex', gap: 8, margin: '10px 0 4px' }}>
        <button className="ghost" onClick={addRow}>+ организация</button>
        <button className="primary" onClick={run} disabled={busy}>{busy ? 'Расчёт…' : 'Рассчитать распределение'}</button>
      </div>
      {error && <div className="error">{error}</div>}

      {result && (
        <div className="stagger" style={{ marginTop: 16 }}>
          <div className="summary-cards" style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
            <Stat label="Статус" value={result.status === 'Optimal' ? 'оптимально' : result.status} />
            <Stat label="Суммарный эффект" value={money(result.total_effect) + ' руб.'} />
            <Stat label="Использовано бюджета" value={`${money(result.total_spend)} (${Math.round(result.utilization * 100)}%)`} />
            <Stat label="Отобрано организаций" value={result.selected_count} />
            <Stat label="Из них выше порога" value={result.above_threshold_count} />
          </div>

          {allocs.length > 0 && (
            <div className="card chart" style={{ marginTop: 14 }}>
              <Plot
                data={[{
                  type: 'bar',
                  x: allocs.map((a) => a.name),
                  y: allocs.map((a) => a.funding),
                  marker: { color: allocs.map((a) => (a.selected ? '#3d6b35' : '#c9c2b4')) },
                  text: allocs.map((a) => (a.selected ? Math.round(a.funded_share * 100) + '%' : '')),
                  textposition: 'outside',
                  hovertemplate: '%{x}<br>финансирование: %{y:,.0f} руб.<extra></extra>',
                }]}
                layout={{
                  title: 'Распределение финансирования по организациям',
                  height: 340, margin: { t: 40, r: 10, b: 90, l: 60 },
                  yaxis: { title: 'руб.' }, font: { family: 'Georgia, serif', size: 12 },
                  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>
          )}

          <div style={{ overflowX: 'auto', marginTop: 12 }}>
            <table style={tableStyle}>
              <thead>
                <tr>{['Организация', 'Решение', 'Финансирование', 'Доля', 'Эффект', 'КЭц', 'Зрелость'].map((h) => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}</tr>
              </thead>
              <tbody>
                {allocs.map((a) => (
                  <tr key={a.key}>
                    <td style={tdStyle}>{a.name}</td>
                    <td style={tdStyle}>
                      <span className={`badge ${a.selected ? 'ok' : 'bad'}`}>
                        {a.selected ? 'финансировать' : 'отклонить'}
                      </span>
                      {a.above_threshold && <span className="badge mid" style={{ marginLeft: 6 }}>выше порога</span>}
                    </td>
                    <td style={tdStyle}>{money(a.funding)}</td>
                    <td style={tdStyle}>{Math.round(a.funded_share * 100)}%</td>
                    <td style={tdStyle}>{money(a.effect)}</td>
                    <td style={tdStyle}>{a.score.toFixed(2).replace('.', ',')}</td>
                    <td style={tdStyle}>{(a.maturity ?? 0).toFixed(2).replace('.', ',')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Optimization() {
  const { user } = useAuth()
  return user?.role === 'organization' ? <OrgOptimization /> : <PortfolioOptimization />
}

function OrgOptimization() {
  const [budget, setBudget] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function run() {
    setError(''); setResult(null); setBusy(true)
    try {
      const res = await api.optimizeMine({ budget: budget === '' ? null : num(budget), threshold: 1.0 })
      setResult(res)
    } catch (ex) { setError(ex.message) } finally { setBusy(false) }
  }

  const a = result?.allocations?.[0]
  return (
    <div>
      <h2 className="page-title">Оптимальный уровень затрат на цифровизацию</h2>
      <p className="muted">Расчёт по фактическим показателям вашей организации. Решатель PuLP/CBC; учитывается предел кредитоспособности (по запасу DSCR).</p>
      <p className="jotform-link">Обновить фактические показатели: <a href="https://form.jotform.com/222133487281353" target="_blank" rel="noopener noreferrer">анкета эффективности</a>.</p>
      <div className="form-grid" style={{ maxWidth: 460, marginBottom: 12 }}>
        <label>Бюджет, руб. (необязательно — по умолчанию полная стоимость проекта)
          <input inputMode="decimal" value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="авто" />
        </label>
      </div>
      <button className="primary" onClick={run} disabled={busy}>{busy ? 'Расчёт…' : 'Рассчитать оптимальный уровень затрат'}</button>
      {error && <div className="error" style={{ marginTop: 12 }}>{error}</div>}
      {result && a && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 16 }}>
          <Stat label="Оптимальный уровень затрат" value={money(a.funding) + ' руб.'} />
          <Stat label="Доля от полной стоимости" value={`${Math.round(a.funded_share * 100)}%`} />
          <Stat label="Ожидаемый эффект (ЧДД)" value={money(a.effect) + ' руб.'} />
          <Stat label="КЭц" value={(a.score ?? 0).toFixed(2).replace('.', ',')} />
          <Stat label="Цифровая зрелость" value={(a.maturity ?? 0).toFixed(2).replace('.', ',')} />
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="card" style={{ padding: '12px 16px', minWidth: 150 }}>
      <div className="muted" style={{ fontSize: 13 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>{value}</div>
    </div>
  )
}

const tableStyle = { width: '100%', borderCollapse: 'collapse', fontSize: 14 }
const thStyle = { textAlign: 'left', padding: '8px 10px', borderBottom: '2px solid #d8d2c4', whiteSpace: 'nowrap' }
const tdStyle = { padding: '6px 10px', borderBottom: '1px solid #ece8df', verticalAlign: 'middle' }
const cell = { width: '100%', minWidth: 130 }
const cellNum = { width: 110 }
