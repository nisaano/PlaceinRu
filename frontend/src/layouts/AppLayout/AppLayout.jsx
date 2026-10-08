import { useState } from 'react'
import { useAuth } from '../../auth/AuthContext'
import { Icon } from '../../components/common/Icon'
import { Link, RouterProvider } from '../../router/Router'
import './AppLayout.css'

const primaryNav = [
  ['Миша', '/app/misha', 'chat'],
  ['Мои путешествия', '/app/trips', 'trip'],
  ['Избранное', '/app/favorites', 'heart'],
]
const categories = [
  ['Билеты', 'ticket'],
  ['Отели', 'bed'],
  ['Достопримечательности', 'landmark'],
  ['Рестораны', 'food'],
  ['Гиды', 'guide'],
  ['Документы', 'file'],
]

export function AppLayout({ children }) {
  const { user, logout } = useAuth()
  const { path, navigate } = RouterProvider.useRouter()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const closeDrawer = () => setDrawerOpen(false)
  return (
    <div className="app-frame">
      <header className="app-mobile-header">
        <button aria-label="Открыть меню" onClick={() => setDrawerOpen(true)}>
          <Icon name="menu" />
        </button>
        <Link className="landing-brand" to="/app">
          <span className="brand-pin">
            <Icon name="pin" size={18} />
          </span>
          <b>PlaceinRu</b>
        </Link>
        <button aria-label="Профиль" onClick={() => navigate('/app/profile')}>
          <Icon name="user" />
        </button>
      </header>
      {drawerOpen && (
        <button className="app-drawer-scrim" aria-label="Закрыть меню" onClick={closeDrawer} />
      )}
      <aside className={`app-sidebar ${drawerOpen ? 'is-open' : ''}`}>
        <Link className="app-sidebar__brand" to="/app" onClick={closeDrawer}>
          <span className="brand-pin">
            <Icon name="pin" size={19} />
          </span>
          <b>PlaceinRu</b>
        </Link>
        <nav className="app-sidebar__nav" aria-label="Разделы кабинета">
          {primaryNav.map(([label, href, icon]) => (
            <Link
              key={href}
              className={`sidebar-link ${path === href ? 'is-active' : ''}`}
              to={href}
              onClick={closeDrawer}
            >
              <Icon name={icon} size={19} />
              <span>{label}</span>
            </Link>
          ))}
          <span className="sidebar-caption">Категории</span>
          {categories.map(([label, icon]) => (
            <button
              className="sidebar-link sidebar-link--button"
              key={label}
              onClick={() => {
                sessionStorage.setItem('placeinru.category', label)
                navigate('/app/trips')
                closeDrawer()
              }}
            >
              <Icon name={icon} size={18} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="app-sidebar__bottom">
          <button
            className="profile-link"
            onClick={() => {
              navigate('/app/profile')
              closeDrawer()
            }}
          >
            <span className="profile-avatar">
              {(user?.name || user?.email || 'П').slice(0, 1).toUpperCase()}
            </span>
            <span>
              <b>{user?.name || user?.email || 'Путешественник'}</b>
              <small>Профиль и настройки</small>
            </span>
          </button>
          <button
            className="sidebar-logout"
            onClick={() => {
              logout()
              navigate('/login')
            }}
          >
            Выйти из аккаунта
          </button>
        </div>
      </aside>
      <main className="app-main">
        {import.meta.env.VITE_ENABLE_DEMO_MODE === 'true' && (
          <div className="demo-mode-banner">
            <Icon name="alert" size={16} /> Режим разработки: синтетические данные будут явно
            помечены как демо
          </div>
        )}
        {children}
      </main>
    </div>
  )
}
