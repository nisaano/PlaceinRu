import { useEffect } from 'react'
import { AuthProvider } from './auth/AuthProvider'
import { useAuth } from './auth/AuthContext'
import { RouterProvider } from './router/Router'
import { AppLayout } from './layouts/AppLayout/AppLayout'
import { LandingPage } from './pages/LandingPage/LandingPage'
import { AuthPage } from './pages/AuthPage/AuthPage'
import { DashboardPage } from './pages/DashboardPage/DashboardPage'
import { MishaPage } from './pages/MishaPage/MishaPage'
import { TripsPage } from './pages/TripsPage/TripsPage'
import { TripPage } from './pages/TripPage/TripPage'
import { FavoritesPage } from './pages/FavoritesPage/FavoritesPage'
import { ProfilePage } from './pages/ProfilePage/ProfilePage'

function RoutedApp() {
  const { path, navigate } = RouterProvider.useRouter()
  const { user, loading } = useAuth()
  const match = path.match(/^\/app\/trips\/([^/?]+)(?:\/([^/?]+))?$/)
  const tripMatch = match ? { id: match[1], tab: match[2] || 'overview' } : null

  useEffect(() => {
    if (!loading && path.startsWith('/app') && !user) navigate('/login', { replace: true })
  }, [loading, path, user, navigate])

  if (path === '/' || !path) return <LandingPage />
  if (path === '/login') return <AuthPage mode="login" />
  if (path === '/register') return <AuthPage mode="register" />

  if (!path.startsWith('/app')) return <NotFound />
  if (loading)
    return (
      <div className="app-loading">
        <span className="spinner" />
        Проверяем ваш аккаунт…
      </div>
    )
  if (!user) return null

  return (
    <AppLayout>
      {path === '/app' && <DashboardPage />}
      {path.startsWith('/app/misha') && (
        <MishaPage tripId={new URLSearchParams(path.split('?')[1] || '').get('tripId')} />
      )}
      {path === '/app/trips' && <TripsPage />}
      {tripMatch && <TripPage key={tripMatch.id} tripId={tripMatch.id} activeTab={tripMatch.tab} />}
      {path === '/app/favorites' && <FavoritesPage />}
      {path === '/app/profile' && <ProfilePage />}
      {!['/app', '/app/trips', '/app/favorites', '/app/profile'].includes(path) &&
        !path.startsWith('/app/misha') &&
        !tripMatch && <NotFound />}
    </AppLayout>
  )
}

function NotFound() {
  const { navigate } = RouterProvider.useRouter()
  return (
    <main className="not-found">
      <span className="eyebrow">PlaceinRU</span>
      <h1>Такой страницы пока нет</h1>
      <button className="button button--primary" onClick={() => navigate('/')}>
        На главную
      </button>
    </main>
  )
}

export default function App() {
  return (
    <RouterProvider>
      <AuthProvider>
        <RoutedApp />
      </AuthProvider>
    </RouterProvider>
  )
}
