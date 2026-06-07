import { useEffect, useState } from 'react'
import Plotly from 'plotly.js-basic-dist-min'
import createPlotlyComponent from 'react-plotly.js/factory'
import { api } from '../api.js'
import BelarusChoropleth from './BelarusChoropleth.jsx'

const Plot = createPlotlyComponent(Plotly)

const COLORS = { green: '#2d6a4f', amber: '#d4a017', red: '#c1432f', grey: '#9aa39b' }
const zoneColor = (zone) =>
  zone === 'эффективна' || zone === 'высокая' ? COLORS.green
  : zone === 'неэффективна' || zone === 'низкая' ? COLORS.red
  : COLORS.amber

const FONT = { family: 'PT Sans, system-ui, sans-serif', size: 12, color: '#1f2a24' }
const baseLayout = (title, extra = {}) => ({
  title: { text: title, font: { family: 'Spectral, serif', size: 16, color: '#1b4332' } },
  font: FONT, margin: { t: 46, r: 16, b: 80, l: 56 }, paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)', showlegend: false, ...extra,
})
const CONFIG = { displayModeBar: false, responsive: true }
const plotStyle = { width: '100%', height: '340px' }

export default function Reports() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [orgId, setOrgId] = useState('')
  const [orgRep, setOrgRep] = useState(null)
  const [busy, setBusy] = useState('')
  const [exportError, setExportError] = useState('')

  useEffect(() => { api.summary().then(setData).catch((e) => setError(e.message)) }, [])
  useEffect(() => {
    if (!orgId) { setOrgRep(null); return }
    api.organizationReport(orgId).then(setOrgRep).catch(() => setOrgRep(null))
  }, [orgId])

  async function exportFile(fmt) {
    setBusy(fmt); setExportError('')
    try { await api.download(`/reports/export.${fmt}`, `АгроЦифра_отчёт.${fmt}`) }
    catch (e) { setExportError(e.message || 'Не удалось сформировать файл экспорта') }
    finally { setBusy('') }
  }

  if (error) return <div className="error">{error}</div>
  if (!data) return <div className="muted">Загрузка…</div>

  const eff = data.efficiency_by_org
  const mat = data.maturity_by_org
  const regions = data.by_region.filter((r) => r.mean_ke != null)
  const districts = (data.by_district || []).filter((r) => r.mean_ke != null || r.mean_maturity != null)

  return (
    <div className="stagger">
      <div className="reports-head">
        <h2 className="page-title">Отчёты и визуализация</h2>
        <div className="export-bar">
          <span className="muted">Экспорт:</span>
          <button className="ghost" disabled={busy} onClick={() => exportFile('docx')}>{busy === 'docx' ? '…' : 'Word'}</button>
          <button className="ghost" disabled={busy} onClick={() => exportFile('xlsx')}>{busy === 'xlsx' ? '…' : 'Excel'}</button>
          <button className="ghost" disabled={busy} onClick={() => exportFile('pdf')}>{busy === 'pdf' ? '…' : 'PDF'}</button>
        </div>
      </div>
      {exportError && <div className="error" style={{ marginTop: 8 }}>{exportError}</div>}

      {eff.length === 0 && mat.length === 0 && (
        <p className="muted">Нет данных для визуализации. Введите или импортируйте оценки.</p>
      )}

      {eff.length > 0 && (
        <div className="card chart">
          <Plot
            data={[
              {
                type: 'bar', x: eff.map((r) => r.name), y: eff.map((r) => r.coefficient),
                marker: { color: eff.map((r) => zoneColor(r.zone)) },
                text: eff.map((r) => r.coefficient.toFixed(2).replace('.', ',')),
                textposition: 'outside', hovertemplate: '%{x}<br>КЭц = %{y:.2f}<extra></extra>',
              },
            ]}
            layout={baseLayout('Коэффициент эффективности цифровизации (КЭц) по организациям', {
              yaxis: { title: 'КЭц', zeroline: false },
              xaxis: { tickangle: -35, automargin: true },
              shapes: [{ type: 'line', x0: -0.5, x1: eff.length - 0.5, y0: 1, y1: 1,
                line: { color: COLORS.grey, width: 1.5, dash: 'dash' } }],
              annotations: [{ x: eff.length - 0.5, y: 1, xanchor: 'right', yanchor: 'bottom',
                text: 'порог 1,0', showarrow: false, font: { size: 11, color: COLORS.grey } }],
            })}
            config={CONFIG} style={plotStyle} useResizeHandler
          />
        </div>
      )}

      {mat.length > 0 && (
        <div className="card chart">
          <Plot
            data={[
              {
                type: 'bar', x: mat.map((r) => r.name), y: mat.map((r) => r.maturity),
                marker: { color: mat.map((r) => zoneColor(r.zone)) },
                text: mat.map((r) => r.maturity.toFixed(2).replace('.', ',')),
                textposition: 'outside', hovertemplate: '%{x}<br>зрелость = %{y:.2f}<extra></extra>',
              },
            ]}
            layout={baseLayout('Уровень цифровой зрелости по организациям', {
              yaxis: { title: 'Зрелость', range: [0, Math.max(0.8, ...mat.map((r) => r.maturity)) + 0.1] },
              xaxis: { tickangle: -35, automargin: true },
              shapes: [0.134, 0.366].map((y) => ({ type: 'line', x0: -0.5, x1: mat.length - 0.5,
                y0: y, y1: y, line: { color: COLORS.grey, width: 1, dash: 'dot' } })),
            })}
            config={CONFIG} style={plotStyle} useResizeHandler
          />
        </div>
      )}

      {regions.length > 0 && (
        <div className="map-grid">
          <BelarusChoropleth
            title="Среднее КЭц по регионам"
            unit="КЭц"
            values={Object.fromEntries(
              data.by_region.filter((r) => r.mean_ke != null).map((r) => [r.region, r.mean_ke]),
            )}
          />
          <BelarusChoropleth
            title="Средняя цифровая зрелость по регионам"
            unit="КЗ"
            values={Object.fromEntries(
              data.by_region.filter((r) => r.mean_maturity != null).map((r) => [r.region, r.mean_maturity]),
            )}
          />
        </div>
      )}

      {districts.length > 0 && (
        <div className="map-grid">
          <BelarusChoropleth
            level="district"
            title="Среднее КЭц по районам"
            unit="КЭц"
            values={Object.fromEntries(
              data.by_district.filter((r) => r.mean_ke != null).map((r) => [r.district, r.mean_ke]),
            )}
          />
          <BelarusChoropleth
            level="district"
            title="Средняя цифровая зрелость по районам"
            unit="КЗ"
            values={Object.fromEntries(
              data.by_district.filter((r) => r.mean_maturity != null).map((r) => [r.district, r.mean_maturity]),
            )}
          />
        </div>
      )}

      {eff.length > 0 && (
        <div className="card">
          <h3 className="section" style={{ marginTop: 0 }}>Сравнение «до / после» цифровизации</h3>
          <label className="select-row">Организация:
            <select value={orgId} onChange={(e) => setOrgId(e.target.value)}>
              <option value="">— выберите —</option>
              {eff.map((r) => <option key={r.organization_id} value={r.organization_id}>{r.name}</option>)}
            </select>
          </label>
          {orgRep && orgRep.before_after.length > 0 ? (
            <>
              <Plot
                data={[
                  { type: 'bar', name: 'ДО', x: orgRep.before_after.map((b) => b.indicator),
                    y: orgRep.before_after.map(() => 100), marker: { color: COLORS.grey },
                    hovertemplate: 'ДО: %{x}<extra></extra>' },
                  { type: 'bar', name: 'ПОСЛЕ', x: orgRep.before_after.map((b) => b.indicator),
                    y: orgRep.before_after.map((b) => Math.round((b.after / b.before) * 1000) / 10),
                    marker: { color: COLORS.green },
                    text: orgRep.before_after.map((b) => (b.change_pct >= 0 ? '+' : '') + b.change_pct + '%'),
                    textposition: 'outside',
                    hovertemplate: 'ПОСЛЕ: %{x}<br>%{y}% к уровню ДО<extra></extra>' },
                ]}
                layout={baseLayout(`«До / после» — ${orgRep.name}`, {
                  barmode: 'group', showlegend: true,
                  legend: { orientation: 'h', y: -0.25 },
                  yaxis: { title: '% к уровню ДО (ДО = 100%)' },
                  xaxis: { tickangle: -25, automargin: true },
                })}
                config={CONFIG} style={plotStyle} useResizeHandler
              />
              <table className="grid" style={{ marginTop: 12 }}>
                <thead><tr><th>Показатель</th><th>До</th><th>После</th><th>Δ, %</th><th>Ед.</th></tr></thead>
                <tbody>
                  {orgRep.before_after.map((b) => (
                    <tr key={b.indicator}>
                      <td>{b.indicator}</td>
                      <td className="num">{b.before}</td>
                      <td className="num">{b.after}</td>
                      <td className="num strong" style={{ color: b.change_pct >= 0 ? COLORS.green : COLORS.red }}>
                        {b.change_pct >= 0 ? '+' : ''}{b.change_pct}
                      </td>
                      <td className="muted">{b.unit}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : orgId ? <p className="muted">Для организации нет сопоставимых данных «до/после».</p> : null}
        </div>
      )}
    </div>
  )
}
