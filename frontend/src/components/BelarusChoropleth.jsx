import geoRaw from '../assets/geo/belarus_adm1.geojson?raw'

// Карта областей Беларуси (ADM1). Рендер — собственный SVG c равнопромежуточной
// проекцией (без внешних зависимостей; базовый бандл Plotly не содержит choropleth).
const GEO = JSON.parse(geoRaw)

// Соответствие наименований GeoJSON (англ.) и областей (рус.)
const RU_BY_EN = {
  Brest: 'Брестская', Vitebsk: 'Витебская', Gomel: 'Гомельская',
  Grodno: 'Гродненская', Minsk: 'Минская', Mogilev: 'Могилёвская',
  'Minsk City': 'г. Минск',
}

function polysOf(feature) {
  const g = feature.geometry
  if (g.type === 'Polygon') return [g.coordinates]
  if (g.type === 'MultiPolygon') return g.coordinates
  return []
}

// Границы всех координат и параметры проекции (вычисляются один раз)
const ALL = []
GEO.features.forEach((f) => polysOf(f).forEach((poly) => poly.forEach((ring) =>
  ring.forEach(([lon, lat]) => ALL.push([lon, lat])))))
const minLon = Math.min(...ALL.map((p) => p[0]))
const maxLon = Math.max(...ALL.map((p) => p[0]))
const minLat = Math.min(...ALL.map((p) => p[1]))
const maxLat = Math.max(...ALL.map((p) => p[1]))
const KX = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180)  // коррекция по широте
const PROJ_W = (maxLon - minLon) * KX
const PROJ_H = maxLat - minLat
const W = 640
const PAD = 10
const H = Math.round((W * PROJ_H) / PROJ_W)
const SCALE = Math.min((W - 2 * PAD) / PROJ_W, (H - 2 * PAD) / PROJ_H)
const OX = (W - PROJ_W * SCALE) / 2
const OY = (H - PROJ_H * SCALE) / 2
const px = (lon) => OX + (lon - minLon) * KX * SCALE
const py = (lat) => OY + (maxLat - lat) * SCALE

function buildFeature(feature) {
  const polys = polysOf(feature)
  const d = polys.map((poly) => poly.map((ring) =>
    ring.map(([lon, lat], i) => `${i ? 'L' : 'M'}${px(lon).toFixed(1)} ${py(lat).toFixed(1)}`).join(' ') + 'Z'
  ).join(' ')).join(' ')
  // центроид — среднее вершин наибольшего внешнего контура (для подписи)
  let outer = []
  for (const poly of polys) if (poly[0].length > outer.length) outer = poly[0]
  const cx = outer.reduce((s, p) => s + px(p[0]), 0) / outer.length
  const cy = outer.reduce((s, p) => s + py(p[1]), 0) / outer.length
  return { en: feature.properties.shapeName, ru: RU_BY_EN[feature.properties.shapeName], d, cx, cy }
}

const FEATURES = GEO.features.map(buildFeature)

function colorFor(v, min, max) {
  if (v == null) return '#e7e9e6'
  const t = max > min ? (v - min) / (max - min) : 0.5
  const c1 = [206, 228, 211]   // светло-зелёный
  const c2 = [27, 67, 50]      // тёмно-зелёный
  const m = (a, b) => Math.round(a + (b - a) * t)
  return `rgb(${m(c1[0], c2[0])},${m(c1[1], c2[1])},${m(c1[2], c2[2])})`
}

const fmtDefault = (v) => v.toFixed(2).replace('.', ',')

export default function BelarusChoropleth({ title, values, unit = '', format = fmtDefault }) {
  const present = Object.values(values).filter((v) => v != null)
  const min = present.length ? Math.min(...present) : 0
  const max = present.length ? Math.max(...present) : 1
  return (
    <div className="card chart">
      <h3 className="map-title">{title}</h3>
      <svg viewBox={`0 0 ${W} ${H}`} className="belarus-map" role="img" aria-label={title}>
        {FEATURES.map((f) => {
          const v = f.ru ? values[f.ru] : null
          return (
            <path key={f.en} d={f.d} fill={colorFor(v, min, max)} stroke="#ffffff"
              strokeWidth="1" className="map-region">
              <title>{f.ru || f.en}: {v == null ? 'нет данных' : format(v) + (unit ? ` ${unit}` : '')}</title>
            </path>
          )
        })}
        {FEATURES.filter((f) => f.ru && f.en !== 'Minsk City').map((f) => {
          const v = values[f.ru]
          return (
            <text key={`t-${f.en}`} x={f.cx} y={f.cy} className="map-label" textAnchor="middle">
              <tspan x={f.cx} dy="-2">{f.ru.replace('ская', '.')}</tspan>
              <tspan x={f.cx} dy="14" className="map-label-val">{v == null ? '—' : format(v)}</tspan>
            </text>
          )
        })}
      </svg>
      <div className="map-legend">
        <span className="muted">{unit || 'значение'}:</span>
        <span>{present.length ? format(min) : '—'}</span>
        <span className="legend-bar" />
        <span>{present.length ? format(max) : '—'}</span>
        <span className="legend-na"><i /> нет данных</span>
      </div>
    </div>
  )
}
