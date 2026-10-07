import { useCallback, useEffect, useState } from 'react'
import { mrtApi } from '../../api/mrt'
import { tripsApi } from '../../api/trips'
import { useAuth } from '../../auth/AuthContext'
import { readableError } from '../../api/client'
import { Icon } from '../../components/common/Icon'
import { ErrorNotice, LoadingState } from '../../components/common/Feedback'
import { Link, RouterProvider } from '../../router/Router'
import mishaLandscape from '../../assets/figma/assistant-background.png'
import './DashboardPage.css'

const money = (amount, currency = 'RUB') =>
  amount == null
    ? 'Не указан'
    : new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency,
        maximumFractionDigits: 0,
      }).format(Number(amount))

export function DashboardPage() {
  const { navigate } = RouterProvider.useRouter()
  const { user } = useAuth()
  const [trips, setTrips] = useState([])
  const [regions, setRegions] = useState([])
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [regionError, setRegionError] = useState('')

  const load = useCallback(async () => {
    const [tripResult, regionResult] = await Promise.allSettled([tripsApi.list(), mrtApi.catalog()])
    if (tripResult.status === 'fulfilled') setTrips(tripResult.value || [])
    else
      setError('Не удалось загрузить путешествия. Попробуйте обновить страницу или создайте новое.')
    if (regionResult.status === 'fulfilled') setRegions(regionResult.value?.regions || [])
    else setRegionError(readableError(regionResult.reason))
    setBusy(false)
  }, [])
  const retryLoad = () => {
    setBusy(true)
    setError('')
    setRegionError('')
    load()
  }

  useEffect(() => {
    load()
  }, [load])

  return (
    <section className="dashboard-page">
      <section className="dashboard-hero" aria-labelledby="dashboard-heading">
        <div className="dashboard-hero__content">
          <div className="page-header">
            <div>
              <span className="eyebrow">Привет, {user?.name || 'путешественник'}!</span>
              <h1 id="dashboard-heading">Куда отправимся сегодня?</h1>
              <p>Миша поможет найти направление и собрать планы поездки.</p>
            </div>
            <Link to="/app/misha" className="button button--primary">
              <Icon name="plus" /> Новое путешествие
            </Link>
          </div>
          <form
            className="dashboard-prompt"
            onSubmit={(event) => {
              event.preventDefault()
              sessionStorage.setItem(
                'placeinru.mishaPrompt',
                new FormData(event.currentTarget).get('prompt')?.toString() || '',
              )
              navigate('/app/misha')
            }}
          >
            <Icon name="sparkle" size={23} />
            <input
              name="prompt"
              aria-label="Куда хотите поехать"
              placeholder="Напишите, куда хотите поехать…"
            />
            <button aria-label="Начать с Мишей">
              <Icon name="send" size={19} />
            </button>
          </form>
        </div>
        <img
          className="dashboard-hero__art"
          src={mishaLandscape}
          alt="Миша путешествует по России"
        />
      </section>
      <div className="dashboard-section-title">
        <div>
          <h2>Мои путешествия</h2>
          <p>Поездки из вашего аккаунта</p>
        </div>
        <Link to="/app/trips">
          Все поездки <Icon name="arrow" size={16} />
        </Link>
      </div>
      {busy ? (
        <LoadingState>Загружаем ваши путешествия…</LoadingState>
      ) : error ? (
        <ErrorNotice message={error} onRetry={retryLoad} />
      ) : trips.length ? (
        <div className="dashboard-trip-grid">
          {trips.slice(0, 3).map((trip) => (
            <Link
              to={`/app/trips/${trip.id}/overview`}
              className="dashboard-trip card"
              key={trip.id}
            >
              <span className="trip-chip">{trip.status || 'Путешествие'}</span>
              <div className="dashboard-trip__landscape">
                <Icon name="pin" size={22} />
              </div>
              <h3>{trip.title || trip.destination || 'Поездка'}</h3>
              <p>
                {trip.startDate || 'Дата не указана'}
                {trip.endDate ? ` — ${trip.endDate}` : ''}
              </p>
              <div className="dashboard-trip__meta">
                <span>{(trip.adults || 0) + (trip.children || 0) || '—'} путешественника</span>
                <b>{money(trip.budget, trip.currency || 'RUB')}</b>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="dashboard-empty card">
          <div>
            <span className="dashboard-empty__icon">
              <Icon name="trip" size={24} />
            </span>
            <h3>Твоё первое путешествие начинается здесь</h3>
            <p>Расскажите Мише, куда хочется отправиться — и начните собирать свой маршрут.</p>
          </div>
          <Link className="button button--outline button--small" to="/app/misha">
            Собрать маршрут <Icon name="arrow" size={15} />
          </Link>
        </div>
      )}
      <div className="dashboard-section-title">
        <div>
          <h2>Популярные направления</h2>
          <p>Список направлений из каталога MRT</p>
        </div>
      </div>
      {regionError && <ErrorNotice message={regionError} />}
      {regions.length > 0 && (
        <div className="region-chips">
          {regions.map((region) => (
            <button
              key={region.region_id}
              onClick={() => {
                sessionStorage.setItem('placeinru.mishaPrompt', `Хочу поехать в ${region.name}`)
                navigate('/app/misha')
              }}
            >
              <Icon name="pin" size={17} />
              <span>
                <b>{region.name}</b>
                <small>{region.description}</small>
              </span>
              <Icon name="arrow" size={16} />
            </button>
          ))}
        </div>
      )}
      {!busy && !regions.length && !regionError && (
        <p className="muted-caption">В текущем каталоге пока нет опубликованных направлений.</p>
      )}
    </section>
  )
}
