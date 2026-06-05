import { useState } from 'react'
import { api } from '../api.js'

const GROUPS = [
  ['Экономические показатели', [
    ['cost_total_before', 'Сумма затрат на растениеводство ДО, руб.'],
    ['area_before_ha', 'Площадь обрабатываемых земель ДО, га'],
    ['cost_per_ha_after', 'Затраты на 1 га (после), руб./га'],
    ['yield_before', 'Средняя урожайность ДО, т/га'],
    ['yield_after', 'Средняя урожайность ПОСЛЕ, т/га'],
    ['profit_before', 'Прибыль ДО, руб. (необяз.)'],
    ['profit_after', 'Прибыль ПОСЛЕ, руб. (необяз.)'],
    ['total_costs_before', 'Общие затраты ДО, руб. (необяз.)'],
    ['total_costs', 'Совокупные затраты, руб. (необяз.)'],
  ]],
  ['Экологические показатели', [
    ['petrol_before_t', 'Бензин ДО, т'],
    ['petrol_after_t', 'Бензин ПОСЛЕ, т'],
    ['diesel_before_t', 'Дизтопливо ДО, т'],
    ['diesel_after_t', 'Дизтопливо ПОСЛЕ, т'],
  ]],
  ['Социальные показатели', [
    ['productivity_before', 'Производительность труда ДО, руб./чел.'],
    ['productivity_after', 'Производительность труда ПОСЛЕ, руб./чел.'],
    ['taxes_before', 'Налоги ДО, руб.'],
    ['taxes_after', 'Налоги ПОСЛЕ, руб.'],
  ]],
]
const OPTIONAL = new Set(['profit_before', 'profit_after', 'total_costs_before', 'total_costs'])
const fmt = (x) => Number(x).toFixed(4).replace('.', ',')

export default function EfficiencyForm() {
  const [name, setName] = useState('')
  const [v, setV] = useState({})
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setV((s) => ({ ...s, [k]: e.target.value }))

  async function submit(e) {
    e.preventDefault()
    setError(''); setResult(null); setBusy(true)
    try {
      const payload = { organization_name: name }
      for (const [, fields] of GROUPS) {
        for (const [k] of fields) {
          const raw = (v[k] ?? '').toString().replace(',', '.').trim()
          if (raw === '') {
            if (OPTIONAL.has(k)) { payload[k] = null; continue }
            throw new Error('Заполните все обязательные поля')
          }
          payload[k] = Number(raw)
        }
      }
      const a = await api.createEfficiency(payload)
      setResult(a)
    } catch (ex) { setError(ex.message) } finally { setBusy(false) }
  }

  return (
    <div>
      <h2 className="page-title">Ввод данных · эффективность цифровизации</h2>
      <p className="muted">Интегральный коэффициент КЭц рассчитывается по индексной формуле (произведение средних отношений «после/до»).</p>
      <form onSubmit={submit} className="form">
        <label className="full">Наименование организации
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        {GROUPS.map(([title, fields]) => (
          <fieldset key={title}>
            <legend>{title}</legend>
            <div className="form-grid">
              {fields.map(([k, lbl]) => (
                <label key={k}>{lbl}
                  <input inputMode="decimal" value={v[k] ?? ''} onChange={set(k)}
                    required={!OPTIONAL.has(k)} />
                </label>
              ))}
            </div>
          </fieldset>
        ))}
        {error && <div className="error">{error}</div>}
        <button className="primary" disabled={busy}>{busy ? 'Расчёт…' : 'Рассчитать и сохранить'}</button>
      </form>

      {result && (
        <div className="result-card stagger">
          <h3>Результат</h3>
          <div className="result-main">
            <div className="result-big">{fmt(result.coefficient)}</div>
            <span className={`badge ${result.zone === 'эффективна' ? 'ok' : result.zone === 'неэффективна' ? 'bad' : 'mid'}`}>{result.zone}</span>
          </div>
          <div className="result-parts">
            <span>Экономический индекс: <b>{fmt(result.economic_index)}</b></span>
            <span>Экологический индекс: <b>{fmt(result.ecological_index)}</b></span>
            <span>Социальный индекс: <b>{fmt(result.social_index)}</b></span>
          </div>
        </div>
      )}
    </div>
  )
}
