const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'
const TOKEN_KEY = 'agrocifra_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

async function request(path, { method = 'GET', body, form, auth = true } = {}) {
  const headers = {}
  let payload
  if (form) {
    payload = new URLSearchParams(form)
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
  } else if (body !== undefined) {
    payload = JSON.stringify(body)
    headers['Content-Type'] = 'application/json'
  }
  if (auth) {
    const t = getToken()
    if (t) headers['Authorization'] = `Bearer ${t}`
  }
  const res = await fetch(`${API_BASE}${path}`, { method, headers, body: payload })
  if (!res.ok) {
    let detail
    try { detail = (await res.json()).detail } catch { detail = res.statusText }
    const err = new Error(typeof detail === 'string' ? detail : `Ошибка ${res.status}`)
    err.status = res.status
    throw err
  }
  return res.status === 204 ? null : res.json()
}

export const api = {
  login: (username, password) =>
    request('/auth/login', { method: 'POST', form: { username, password }, auth: false }),
  me: () => request('/auth/me'),
  register: (payload) => request('/auth/register', { method: 'POST', body: payload, auth: false }),
  pendingUsers: () => request('/auth/pending'),
  activateUser: (id) => request(`/auth/users/${id}/activate`, { method: 'POST' }),
  switchRole: (role) => request('/auth/switch-role', { method: 'POST', body: { role } }),
  organizations: () => request('/data/organizations'),
  efficiencyAssessments: () => request('/data/assessments/efficiency'),
  maturityAssessments: () => request('/data/assessments/maturity'),
  createEfficiency: (payload) =>
    request('/data/assessments/efficiency', { method: 'POST', body: payload }),
  createMaturity: (payload) =>
    request('/data/assessments/maturity', { method: 'POST', body: payload }),
  syncEfficiency: () => request('/data/etl/jotform/efficiency/sync', { method: 'POST' }),
  syncMaturity: () => request('/data/etl/jotform/maturity/sync', { method: 'POST' }),
  async importModel(file, orgName, dscrNorm) {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('organization_name', orgName)
    if (dscrNorm !== undefined && dscrNorm !== null && dscrNorm !== '') fd.append('dscr_norm', dscrNorm)
    const res = await fetch(`${API_BASE}/optimization/projects/import-model`, {
      method: 'POST', headers: { Authorization: `Bearer ${getToken()}` }, body: fd,
    })
    if (!res.ok) {
      let msg = 'Не удалось импортировать модель'
      try { const e = await res.json(); msg = e.detail || msg } catch { /* ignore */ }
      throw new Error(msg)
    }
    return res.json()
  },
  optimize: (payload) => request('/optimization/run', { method: 'POST', body: payload }),
  optimizationRuns: () => request('/optimization/runs'),
  optimizationRun: (id) => request(`/optimization/runs/${id}`),
  summary: () => request('/reports/summary'),
  organizationReport: (id) => request(`/reports/organization/${id}`),
  async download(path, filename) {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!res.ok) throw new Error('Не удалось сформировать файл экспорта')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  },
}

export { API_BASE }
