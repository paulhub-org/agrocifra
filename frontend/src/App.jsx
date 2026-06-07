import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import { useOrgGate } from './orgGate.jsx'
import Layout from './components/Layout.jsx'
import Login from './components/Login.jsx'
import Dashboard from './components/Dashboard.jsx'
import Organizations from './components/Organizations.jsx'
import Assessments from './components/Assessments.jsx'
import Reports from './components/Reports.jsx'
import Optimization from './components/Optimization.jsx'
import EfficiencyForm from './components/EfficiencyForm.jsx'
import MaturityForm from './components/MaturityForm.jsx'
import PendingUsers from './components/PendingUsers.jsx'
import Recommendations from './components/Recommendations.jsx'

const DATA_ENTRY = ['organization', 'digitalization_office']
const OPT_ROLES = ['digitalization_office', 'state_authority', 'organization']
const ADMIN_ROLES = ['digitalization_office', 'state_authority']
// «Штабные» роли (без «Организации») — задачи 13/15
const STAFF_ROLES = ['regional_operator', 'district_operator', 'digitalization_office', 'state_authority']

function Protected({ children, roles }) {
  const { token, user, loading } = useAuth()
  if (!token) return <Navigate to="/login" replace />
  if (loading) return <div className="center muted">Загрузка…</div>
  if (roles && user && !roles.includes(user.role))
    return <div className="card notice">Недостаточно прав для просмотра этого раздела.</div>
  return children
}

// «Дашборд» и «Оценки» для роли «Организация» доступны только при наличии данных (задача 14)
function RequireOrgData({ children }) {
  const { user } = useAuth()
  const { ready, hasData } = useOrgGate()
  if (user?.role === 'organization') {
    if (!ready) return <div className="center muted">Загрузка…</div>
    if (!hasData) return <Navigate to="/entry/maturity" replace />
  }
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route index element={<RequireOrgData><Dashboard /></RequireOrgData>} />
        <Route path="organizations"
          element={<Protected roles={STAFF_ROLES}><Organizations /></Protected>} />
        <Route path="assessments"
          element={<RequireOrgData><Assessments /></RequireOrgData>} />
        <Route path="reports"
          element={<Protected roles={STAFF_ROLES}><Reports /></Protected>} />
        <Route path="optimization"
          element={<Protected roles={OPT_ROLES}><Optimization /></Protected>} />
        <Route path="recommendations" element={<Recommendations />} />
        <Route path="entry/efficiency"
          element={<Protected roles={DATA_ENTRY}><EfficiencyForm /></Protected>} />
        <Route path="entry/maturity"
          element={<Protected roles={DATA_ENTRY}><MaturityForm /></Protected>} />
        <Route path="pending"
          element={<Protected roles={ADMIN_ROLES}><PendingUsers /></Protected>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
