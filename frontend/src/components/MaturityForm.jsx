import { useState } from 'react'
import { api } from '../api.js'

const fmt = (x) => Number(x).toFixed(3).replace('.', ',')

export default function MaturityForm() {
  const [name, setName] = useState('')
  const [need, setNeed] = useState('')
  const [cap, setCap] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError(''); setResult(null); setBusy(true)
    try {
      const payload = {
        organization_name: name,
        need_avg: Number(need.replace(',', '.')),
        capability_avg: Number(cap.replace(',', '.')),
      }
      const a = await api.createMaturity(payload)
      setResult(a)
    } catch (ex) { setError(ex.message) } finally { setBusy(false) }
  }

  return (
    <div>
      <h2 className="page-title">Ввод данных · цифровая зрелость</h2>
      <p className="muted">Уровень зрелости = геометрическое среднее оценок потребности и возможностей: КЗ = √(потребность · возможности); пороги зон 0,134 и 0,366.</p>
      <form onSubmit={submit} className="form">
        <label className="full">Наименование организации
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <div className="form-grid">
          <label>Среднее значение показателей потребности
            <input inputMode="decimal" value={need} onChange={(e) => setNeed(e.target.value)} required />
          </label>
          <label>Среднее значение показателей возможностей
            <input inputMode="decimal" value={cap} onChange={(e) => setCap(e.target.value)} required />
          </label>
        </div>
        {error && <div className="error">{error}</div>}
        <button className="primary" disabled={busy}>{busy ? 'Расчёт…' : 'Рассчитать и сохранить'}</button>
      </form>

      {result && (
        <div className="result-card stagger">
          <h3>Результат</h3>
          <div className="result-main">
            <div className="result-big">{fmt(result.maturity)}</div>
            <span className={`badge ${result.zone === 'высокая' ? 'ok' : result.zone === 'низкая' ? 'bad' : 'mid'}`}>{result.zone} цифровая зрелость</span>
          </div>
          <div className="result-parts">
            <span>Потребность: <b>{fmt(result.need_avg)}</b></span>
            <span>Возможности: <b>{fmt(result.capability_avg)}</b></span>
          </div>
        </div>
      )}
    </div>
  )
}
