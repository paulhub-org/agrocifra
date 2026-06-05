import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth.jsx'

const NAV = [
  { to: '/', label: 'Дашборд', end: true },
  { to: '/organizations', label: 'Организации' },
  { to: '/assessments', label: 'Оценки' },
  { to: '/reports', label: 'Отчёты' },
  { to: '/optimization', label: 'Оптимизация', roles: ['digitalization_office', 'state_authority'] },
  { to: '/entry/efficiency', label: 'Ввод · эффективность', roles: ['organization', 'digitalization_office'] },
  { to: '/entry/maturity', label: 'Ввод · зрелость', roles: ['organization', 'digitalization_office'] },
]

export default function Layout() {
  const { user, roleLabel, logout } = useAuth()
  const navigate = useNavigate()
  const items = NAV.filter((i) => !i.roles || (user && i.roles.includes(user.role)))
  return (
    <div className="app">
      <aside className="side">
        <div className="brand">
          <span className="logo">🌾</span>
          <div className="brand-text"><b>АгроЦифра</b><small>АИС цифровизации</small></div>
        </div>
        <nav className="nav-list">
          {items.map((i) => (
            <NavLink key={i.to} to={i.to} end={i.end}
              className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
              {i.label}
            </NavLink>
          ))}
        </nav>
        <div className="side-foot">Растениеводство · Республика Беларусь</div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="who">
            <span className="role-chip">{roleLabel}</span>
            <b>{user?.full_name || user?.login}</b>
          </div>
          <button className="ghost" onClick={() => { logout(); navigate('/login') }}>Выйти</button>
        </header>
        <main className="content"><Outlet /></main>
      </div>
    </div>
  )
}
