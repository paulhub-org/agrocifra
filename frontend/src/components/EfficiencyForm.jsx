import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'

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
const OBLASTS = ['Брестская', 'Витебская', 'Гомельская', 'Гродненская', 'Минская', 'Могилёвская']
const fmt = (x) => Number(x).toFixed(4).replace('.', ',')
const JF_REASON = {
  not_configured: 'Интеграция с Jotform не настроена (нет API-ключа).',
  no_org: 'Учётная запись не привязана к организации.',
  no_submission: 'В Jotform пока нет заявки по вашей организации.',
  mapping_error: 'Не удалось сопоставить поля заявки Jotform.',
}

export default function EfficiencyForm() {
  const [name, setName] = useState('')
  const [v, setV] = useState({})
  const [region, setRegion] = useState('')
  const [district, setDistrict] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setV((s) => ({ ...s, [k]: e.target.value }))
  const { user } = useAuth()
  const isOrg = user?.role === 'organization'
  const [jf, setJf] = useState('')

  async function loadFromJotform(manual) {
    if (manual) setJf('Загрузка из Jotform…')
    try {
      const r = await api.jotformPrefill('efficiency')
      if (r.available) {
        const d = r.data
        if (d.organization_name) setName(d.organization_name)
        if (d.region) setRegion(d.region)
        if (d.district) setDistrict(d.district)
        if (d.values) {
          const nv = {}
          for (const [k, val] of Object.entries(d.values)) {
            if (val != null) nv[k] = String(val).replace('.', ',')
          }
          setV(nv)
        }
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
      payload.region = region || null
      payload.district = district || null
      const a = await api.createEfficiency(payload)
      setResult(a)
    } catch (ex) { setError(ex.message) } finally { setBusy(false) }
  }

  return (
    <div>
      <h2 className="page-title">Ввод данных · эффективность цифровизации</h2>
      <p className="muted">Интегральный коэффициент КЭц рассчитывается по индексной формуле (произведение средних отношений «после/до»).</p>
      <p className="jotform-link">Заполнить через форму Jotform: <a href="https://form.jotform.com/222133487281353" target="_blank" rel="noopener noreferrer">анкета фактических показателей эффективности</a>.</p>
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
            <input value={district} onChange={(e) => setDistrict(e.target.value)} placeholder="например, Ивановский" />
          </label>
        </div>
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
