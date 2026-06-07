import { useEffect, useMemo, useState } from 'react'
import { api } from '../api.js'

// Цвет «светофора» по уровню/зоне показателя
function levelClass(level) {
  if (!level) return 'mid'
  if (level === 'высокий' || level === 'высокая' || level === 'эффективна') return 'ok'
  if (level === 'низкий' || level === 'низкая' || level === 'неэффективна') return 'bad'
  return 'mid'
}

const fmt = (v) => (v == null ? '—' : Number(v).toFixed(2).replace('.', ','))

export default function Recommendations() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [orgId, setOrgId] = useState('')
  const [indicator, setIndicator] = useState('')
  const [region, setRegion] = useState('')
  const [district, setDistrict] = useState('')
  const [busy, setBusy] = useState('')
  const [exportError, setExportError] = useState('')

  useEffect(() => { api.recommendations().then(setData).catch((e) => setError(e.message)) }, [])

  const opts = useMemo(() => {
    const items = data?.items || []
    const orgMap = new Map()
    items.forEach((it) => { if (!orgMap.has(it.organization_id)) orgMap.set(it.organization_id, it.organization) })
    return {
      orgs: [...orgMap].map(([id, name]) => ({ id, name })),
      regions: [...new Set(items.map((i) => i.region).filter((r) => r && r !== 'Не указан'))].sort(),
      districts: [...new Set(items.map((i) => i.district).filter(Boolean))].sort(),
    }
  }, [data])

  if (error) return <div className="error">{error}</div>
  if (!data) return <div className="center muted">Загрузка…</div>

  const filtered = data.items.filter((it) =>
    (!orgId || String(it.organization_id) === String(orgId))
    && (!indicator || it.indicator === indicator)
    && (!region || it.region === region)
    && (!district || it.district === district))

  const groups = []
  const seen = new Map()
  filtered.forEach((it) => {
    if (!seen.has(it.organization_id)) {
      const g = { org: it.organization, region: it.region, district: it.district, items: [] }
      seen.set(it.organization_id, g); groups.push(g)
    }
    seen.get(it.organization_id).items.push(it)
  })

  async function exportFile(f) {
    setBusy(f); setExportError('')
    const qs = new URLSearchParams()
    if (orgId) qs.set('organization_id', orgId)
    if (indicator) qs.set('indicator', indicator)
    if (region) qs.set('region', region)
    if (district) qs.set('district', district)
    const suffix = qs.toString() ? `?${qs}` : ''
    try { await api.download(`/recommendations/export.${f}${suffix}`, `АгроЦифра_рекомендации.${f}`) }
    catch (e) { setExportError(e.message || 'Не удалось сформировать файл экспорта') }
    finally { setBusy('') }
  }

  return (
    <div className="stagger">
      <div className="reports-head">
        <h2 className="page-title">Рекомендации</h2>
        <div className="export-bar">
          <span className="muted">Экспорт:</span>
          <button className="ghost" disabled={busy} onClick={() => exportFile('docx')}>{busy === 'docx' ? '…' : 'Word'}</button>
          <button className="ghost" disabled={busy} onClick={() => exportFile('xlsx')}>{busy === 'xlsx' ? '…' : 'Excel'}</button>
          <button className="ghost" disabled={busy} onClick={() => exportFile('pdf')}>{busy === 'pdf' ? '…' : 'PDF'}</button>
        </div>
      </div>
      {exportError && <div className="error" style={{ marginBottom: 8 }}>{exportError}</div>}

      <p className="muted">
        Рекомендации по повышению показателей: потребность, возможности, цифровая зрелость,
        эффективность цифровизации. Используйте фильтры для формирования выборки.
      </p>

      <div className="rec-filters">
        <label className="select-row">Организация
          <select value={orgId} onChange={(e) => setOrgId(e.target.value)}>
            <option value="">Все организации</option>
            {opts.orgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
          </select>
        </label>
        <label className="select-row">Показатель
          <select value={indicator} onChange={(e) => setIndicator(e.target.value)}>
            <option value="">Все показатели</option>
            {data.indicators.map((i) => <option key={i.key} value={i.key}>{i.label}</option>)}
          </select>
        </label>
        <label className="select-row">Область
          <select value={region} onChange={(e) => setRegion(e.target.value)}>
            <option value="">Все области</option>
            {opts.regions.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        <label className="select-row">Район
          <select value={district} onChange={(e) => setDistrict(e.target.value)}>
            <option value="">Все районы</option>
            {opts.districts.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>
      </div>

      {groups.length === 0 ? (
        <p className="muted">По заданным условиям рекомендации отсутствуют.</p>
      ) : groups.map((g) => (
        <div className="card" key={g.org}>
          <h3 className="section" style={{ marginTop: 0 }}>
            {g.org}
            {g.region && g.region !== 'Не указан'
              ? ` — ${g.region}${g.district ? ', ' + g.district : ''}` : ''}
          </h3>
          {g.items.map((it) => (
            <div className="rec-item" key={it.indicator}>
              <div className="rec-head">
                <strong>{it.indicator_label}</strong>
                {it.level && <span className={`badge ${levelClass(it.level)}`}>{it.level}</span>}
                {it.value != null && <span className="muted rec-val">значение: {fmt(it.value)}</span>}
              </div>
              <p className="rec-text">{it.text}</p>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
