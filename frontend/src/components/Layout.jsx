import { useState } from 'react'
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
  const { user, roleLabel, logout, previewing, switchRole, restoreRole } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const isOffice = user?.role === 'digitalization_office'
  const isAdmin = ['digitalization_office', 'state_authority'].includes(user?.role)
  const VIEW_ROLES = [['state_authority', 'Госорган'], ['regional_operator', 'Региональный оператор'], ['organization', 'Организация']]
  const items = NAV.filter((i) => !i.roles || (user && i.roles.includes(user.role)))
  return (
    <div className="app">
      <aside className="side">
        <div className="brand">
          <span className="logo">🌾</span>
          <div className="brand-text"><b>АгроЦифра</b>
            <a className="brand-sub" href="https://mshp.gov.by/ru/sh-ru/" target="_blank" rel="noopener noreferrer">АИС цифровизации сельскохозяйственных организаций – организации растениеводства</a>
          </div>
        </div>
        <nav className="nav-list">
          {items.map((i) => (
            <NavLink key={i.to} to={i.to} end={i.end}
              className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
              {i.label}
            </NavLink>
          ))}
        </nav>
        <div className="side-foot">© 2026 · АгроЦифра</div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="who">
            <span className="role-chip">{roleLabel}</span>
            {previewing && <span className="badge mid">режим просмотра</span>}
          </div>
          <div className="account">
            <button className="account-btn" onClick={() => setMenuOpen((o) => !o)}>
              <b>{user?.full_name || user?.login}</b><span className="caret">▾</span>
            </button>
            {menuOpen && (
              <div className="account-menu" onMouseLeave={() => setMenuOpen(false)}>
                <div className="account-head">
                  <b>{user?.full_name || user?.login}</b>
                  <small className="muted">{roleLabel}</small>
                </div>
                {isOffice && !previewing && (
                  <>
                    <div className="menu-label">Просмотр в роли</div>
                    {VIEW_ROLES.map(([r, label]) => (
                      <button key={r} className="menu-item"
                        onClick={() => { setMenuOpen(false); switchRole(r).then(() => navigate('/')).catch(() => {}) }}>
                        {label}
                      </button>
                    ))}
                    <div className="menu-sep" />
                  </>
                )}
                {previewing && (
                  <>
                    <button className="menu-item"
                      onClick={() => { setMenuOpen(false); restoreRole(); navigate('/') }}>
                      ← Вернуться к роли «Офис цифровизации»
                    </button>
                    <div className="menu-sep" />
                  </>
                )}
                {isAdmin && (
                  <button className="menu-item"
                    onClick={() => { setMenuOpen(false); navigate('/pending') }}>
                    Заявки на регистрацию
                  </button>
                )}
                <button className="menu-item danger"
                  onClick={() => { setMenuOpen(false); logout(); navigate('/login') }}>
                  Выйти
                </button>
              </div>
            )}
          </div>
        </header>
        <main className="content"><Outlet /></main>
        <footer className="app-footer">
          <div className="footer-col">
            <span className="footer-title">Государственный орган</span>
            <a href="https://mshp.gov.by/ru" target="_blank" rel="noopener noreferrer">Министерство сельского хозяйства и продовольствия Республики Беларусь</a>
          </div>
          <div className="footer-col">
            <span className="footer-title">Региональные операторы</span>
            <a href="https://www.brest-region.gov.by/" target="_blank" rel="noopener noreferrer">Брестский облисполком</a>
            <a href="https://vitebsk-region.gov.by/" target="_blank" rel="noopener noreferrer">Витебский облисполком</a>
            <a href="https://gomel-region.gov.by/ru" target="_blank" rel="noopener noreferrer">Гомельский облисполком</a>
            <a href="https://grodno-region.gov.by/ru" target="_blank" rel="noopener noreferrer">Гродненский облисполком</a>
            <a href="https://minsk-region.gov.by/" target="_blank" rel="noopener noreferrer">Минский облисполком</a>
            <a href="https://mogilev-region.gov.by/" target="_blank" rel="noopener noreferrer">Могилёвский облисполком</a>
          </div>
          <div className="footer-col">
            <span className="footer-title">Разработчик</span>
            <a href="mailto:paul.yukhniuk@gmail.com">Связаться с разработчиком</a>
          </div>
        </footer>
      </div>
    </div>
  )
}
