import { useCallback, useEffect, useMemo, useState } from 'react'
import { tripsApi } from '../../api/trips'
import { readableError } from '../../api/client'
import { ErrorNotice, EmptyNotice, LoadingState } from '../../components/common/Feedback'
import { Icon } from '../../components/common/Icon'
import { Link } from '../../router/Router'
import './TripsPage.css'

const filterTabs = [
  ['upcoming', 'Предстоящие'],
  ['past', 'Прошедшие'],
  ['archive', 'Архив'],
]
const categoryTabs = {
  Билеты: 'tickets',
  Отели: 'hotels',
  Достопримечательности: 'attractions',
  Рестораны: 'restaurants',
  Гиды: 'overview',
  Документы: 'documents',
}
const todayIso = new Date().toISOString().slice(0, 10)
const tripDate = (trip) => (trip.startDate ? new Date(`${trip.startDate}T00:00:00`) : null)
const formatDate = (date) =>
  date
    ? new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }).format(
        date,
      )
    : 'Дата не указана'
const formatMoney = (value, currency = 'RUB') =>
  value == null
    ? 'Бюджет не указан'
    : new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency,
        maximumFractionDigits: 0,
      }).format(Number(value))

export function TripsPage() {
  const [trips, setTrips] = useState([])
  const [filter, setFilter] = useState('upcoming')
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [deleteId, setDeleteId] = useState(null)
  const requestedCategory = sessionStorage.getItem('placeinru.category')
  const requestedTab = categoryTabs[requestedCategory] || null

  const load = useCallback(async () => {
    try {
      setTrips((await tripsApi.list()) || [])
    } catch (reason) {
      setError(readableError(reason))
    } finally {
      setBusy(false)
    }
  }, [])
  const retryLoad = () => {
    setBusy(true)
    setError('')
    load()
  }
  useEffect(() => {
    load()
  }, [load])

  const visibleTrips = useMemo(
    () =>
      trips.filter((trip) => {
        const status = (trip.status || '').toLowerCase()
        if (filter === 'archive') return status.includes('archiv') || status.includes('cancel')
        if (filter === 'past')
          return trip.endDate ? trip.endDate < todayIso && !status.includes('archiv') : false
        return (
          !status.includes('archiv') &&
          !status.includes('cancel') &&
          (!trip.endDate || trip.endDate >= todayIso)
        )
      }),
    [trips, filter],
  )

  const removeTrip = async (tripId) => {
    setDeleteId(tripId)
    setError('')
    try {
      await tripsApi.remove(tripId)
      setTrips((current) => current.filter((trip) => trip.id !== tripId))
    } catch (reason) {
      setError(readableError(reason, 'Не удалось удалить путешествие.'))
    } finally {
      setDeleteId(null)
    }
  }

  return (
    <section className="trips-page">
      <div className="page-header">
        <div>
          <span className="eyebrow">Ваши поездки</span>
          <h1>Мои путешествия</h1>
          <p>Все планы и поездки, сохранённые в вашем аккаунте.</p>
        </div>
        <Link className="button button--primary" to="/app/misha">
          <Icon name="plus" /> Новое путешествие
        </Link>
      </div>
      <div className="trip-filters" role="tablist" aria-label="Фильтр путешествий">
        {filterTabs.map(([key, label]) => (
          <button
            key={key}
            className={filter === key ? 'is-active' : ''}
            role="tab"
            aria-selected={filter === key}
            onClick={() => setFilter(key)}
          >
            {label}
            <span>
              {key === 'upcoming'
                ? trips.filter((trip) => !trip.endDate || trip.endDate >= todayIso).length
                : ''}
            </span>
          </button>
        ))}
      </div>
      {error && <ErrorNotice message={error} onRetry={retryLoad} />}
      {requestedCategory && (
        <div className="notice">
          <Icon name="trip" size={18} />
          <p>
            Вы выбрали раздел «{requestedCategory}». Откройте путешествие, чтобы перейти к его
            данным.
          </p>
        </div>
      )}
      {busy ? (
        <LoadingState>Загружаем список путешествий…</LoadingState>
      ) : visibleTrips.length ? (
        <div className="trips-grid">
          {visibleTrips.map((trip) => (
            <article className="trip-list-card card" key={trip.id}>
              <Link
                className="trip-list-card__image"
                to={`/app/trips/${trip.id}/overview`}
                aria-label={`Открыть поездку ${trip.title || trip.destination}`}
              >
                <Icon name="pin" size={24} />
              </Link>
              <div className="trip-list-card__body">
                <div className="trip-list-card__title">
                  <div>
                    <span className="eyebrow">{trip.status || 'Путешествие'}</span>
                    <h2>{trip.title || trip.destination || 'Без названия'}</h2>
                  </div>
                  <button
                    className="icon-button icon-button--danger"
                    aria-label={`Удалить ${trip.title || trip.destination}`}
                    disabled={deleteId === trip.id}
                    onClick={() => removeTrip(trip.id)}
                  >
                    <Icon name="close" size={17} />
                  </button>
                </div>
                <p className="trip-list-card__route">
                  {trip.origin || 'Отправление не указано'} <Icon name="arrow" size={14} />{' '}
                  {trip.destination || 'Направление не указано'}
                </p>
                <p className="trip-list-card__date">
                  {formatDate(tripDate(trip))}
                  {trip.endDate ? ` — ${formatDate(new Date(`${trip.endDate}T00:00:00`))}` : ''}
                </p>
                <div className="trip-list-card__meta">
                  <span>
                    {trip.adults ?? '—'} взрослых{trip.children ? ` · ${trip.children} детей` : ''}
                  </span>
                  <b>{formatMoney(trip.budget, trip.currency || 'RUB')}</b>
                </div>
                <Link
                  className="button button--outline button--small"
                  onClick={() => sessionStorage.removeItem('placeinru.category')}
                  to={`/app/trips/${trip.id}/${requestedTab || 'overview'}`}
                >
                  {requestedCategory ? `Открыть: ${requestedCategory}` : 'Открыть путешествие'}{' '}
                  <Icon name="arrow" size={15} />
                </Link>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyNotice
          title={
            filter === 'upcoming' ? 'Твоё первое путешествие начинается здесь' : 'Здесь пока пусто'
          }
        >
          Список загружается из Backend. Создайте новую поездку с Мишей или выберите другую вкладку.
        </EmptyNotice>
      )}
    </section>
  )
}
