import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'

const OBLASTS = ['Брестская', 'Витебская', 'Гомельская', 'Гродненская', 'Минская', 'Могилёвская']
const fmt = (x) => Number(x).toFixed(3).replace('.', ',')
const JF_REASON = {
  not_configured: 'Интеграция с Jotform не настроена (нет API-ключа).',
  no_org: 'Учётная запись не привязана к организации.',
  no_submission: 'В Jotform пока нет заявки по вашей организации.',
  mapping_error: 'Не удалось сопоставить поля заявки Jotform.',
}

export default function MaturityForm() {
  const [name, setName] = useState('')
  const [need, setNeed] = useState('')
  const [cap, setCap] = useState('')
  const [region, setRegion] = useState('')
  const [district, setDistrict] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const { user } = useAuth()
  const isOrg = user?.role === 'organization'
  const [jf, setJf] = useState('')

  async function loadFromJotform(manual) {
    if (manual) setJf('Загрузка из Jotform…')
    try {
      const r = await api.jotformPrefill('maturity')
      if (r.available) {
        const d = r.data
        if (d.organization_name) setName(d.organization_name)
        if (d.need_avg != null) setNeed(String(d.need_avg).replace('.', ','))
        if (d.capability_avg != null) setCap(String(d.capability_avg).replace('.', ','))
        if (d.region) setRegion(d.region)
        if (d.district) setDistrict(d.district)
        setJf(`Подставлено из заявки Jotform${r.submitted_at ? ` от ${r.submitted_at}` : ''}.`)
      } else if (manual) {
        setJf(JF_REASON[r.reason] || 'Данные из Jotform недоступны.')
      }
    } catch (ex) {
      if (manual) setJf(ex.message || 'Ошибка обращения к Jotform.')
    }
  }

  useEffect(() => { if (isOrg) loadFromJotform(false) }, [isOrg])  // eslint-disable-line react-hooks/exhaustive-deps

  async function submit(e) {
    e.preventDefault()
    setError(''); setResult(null); setBusy(true)
    try {
      const payload = {
        organization_name: name,
        need_avg: Number(need.replace(',', '.')),
        capability_avg: Number(cap.replace(',', '.')),
        region: region || null,
        district: district || null,
      }
      const a = await api.createMaturity(payload)
      setResult(a)
    } catch (ex) { setError(ex.message) } finally { setBusy(false) }
  }

  return (
    <div>
      <h2 className="page-title">Ввод данных · цифровая зрелость</h2>
      <p className="muted">Уровень зрелости = геометрическое среднее оценок потребности и возможностей: КЗ = √(потребность · возможности); пороги зон 0,134 и 0,366.</p>
      <p className="jotform-link">Заполнить через форму Jotform: <a href="https://form.jotform.com/241376010701342" target="_blank" rel="noopener noreferrer">анкета оценки цифровой зрелости</a>.</p>
      {isOrg && (
        <div style={{ margin: '0 0 12px' }}>
          <button type="button" className="ghost" onClick={() => loadFromJotform(true)}>Загрузить из Jotform</button>
          {jf && <span className="muted" style={{ marginLeft: 10 }}>{jf}</span>}
        </div>
      )}
      <form onSubmit={submit} className="form">
        <label className="full">Наименование организации
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <div className="form-grid">
          <label>Область
            <select value={region} onChange={(e) => setRegion(e.target.value)}>
              <option value="">— не указана —</option>
              {OBLASTS.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </label>
          <label>Район
            <input value={district} onChange={(e) => setDistrict(e.target.value)} placeholder="например, Смолевичский" />
          </label>
        </div>
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
