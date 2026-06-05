import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import Layout from './components/Layout.jsx'
import Login from './components/Login.jsx'
import Dashboard from './components/Dashboard.jsx'
import Organizations from './components/Organizations.jsx'
import Assessments from './components/Assessments.jsx'
import Reports from './components/Reports.jsx'
import Optimization from './components/Optimization.jsx'
import EfficiencyForm from './components/EfficiencyForm.jsx'
import MaturityForm from './components/MaturityForm.jsx'

const DATA_ENTRY = ['organization', 'digitalization_office']
const OPT_ROLES = ['digitalization_office', 'state_authority']

function Protected({ children, roles }) {
  const { token, user, loading } = useAuth()
  if (!token) return <Navigate to="/login" replace />
  if (loading) return <div className="center muted">Загрузка…</div>
  if (roles && user && !roles.includes(user.role))
    return <div className="card notice">Недостаточно прав для просмотра этого раздела.</div>
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route index element={<Dashboard />} />
        <Route path="organizations" element={<Organizations />} />
        <Route path="assessments" element={<Assessments />} />
        <Route path="reports" element={<Reports />} />
        <Route path="optimization"
          element={<Protected roles={OPT_ROLES}><Optimization /></Protected>} />
        <Route path="entry/efficiency"
          element={<Protected roles={DATA_ENTRY}><EfficiencyForm /></Protected>} />
        <Route path="entry/maturity"
          element={<Protected roles={DATA_ENTRY}><MaturityForm /></Protected>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
