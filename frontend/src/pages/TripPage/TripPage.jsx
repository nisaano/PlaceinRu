import { useCallback, useEffect, useMemo, useState } from 'react'
import { tripsApi } from '../../api/trips'
import { readableError } from '../../api/client'
import { EmptyNotice, ErrorNotice, LoadingState } from '../../components/common/Feedback'
import { Icon } from '../../components/common/Icon'
import { Link, RouterProvider } from '../../router/Router'
import './TripPage.css'

const tabs = [
  ['overview', 'Обзор'],
  ['tickets', 'Билеты'],
  ['hotels', 'Отели'],
  ['route', 'Маршрут'],
  ['attractions', 'Достопримечательности'],
  ['restaurants', 'Рестораны'],
  ['budget', 'Бюджет'],
  ['documents', 'Документы'],
]
const categories = {
  tickets: {
    title: 'Билеты',
    keywords: ['transport', 'ticket', 'flight', 'train', 'bus', 'авиа', 'поезд'],
  },
  hotels: { title: 'Отели', keywords: ['hotel', 'stay', 'accommodation', 'отель', 'заселен'] },
  attractions: {
    title: 'Достопримечательности',
    keywords: ['attraction', 'activity', 'sight', 'place', 'музей', 'экскурс', 'место'],
  },
  restaurants: {
    title: 'Рестораны',
    keywords: ['restaurant', 'food', 'restaurant', 'ужин', 'обед', 'кафе'],
  },
}
const money = (value, currency = 'RUB') =>
  value == null
    ? 'Не указано'
    : new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency,
        maximumFractionDigits: 0,
      }).format(Number(value))
const displayDate = (value) =>
  value
    ? new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }).format(
        new Date(`${value}T00:00:00`),
      )
    : 'Дата не указана'
const itemName = (item) => item.objectId || item.type || 'Пункт маршрута'
const itemCategory = (item) => String(item.type || '').toLowerCase()

export function TripPage({ tripId, activeTab }) {
  const { navigate } = RouterProvider.useRouter()
  const [trip, setTrip] = useState(null)
  const [budget, setBudget] = useState(null)
  const [busy, setBusy] = useState(true)
  const [budgetStatus, setBudgetStatus] = useState('idle')
  const [error, setError] = useState('')
  const [budgetError, setBudgetError] = useState('')
  const [showDelete, setShowDelete] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [editValues, setEditValues] = useState(null)
  const [editBusy, setEditBusy] = useState(false)
  const [editError, setEditError] = useState('')

  const loadTrip = useCallback(async () => {
    try {
      setTrip(await tripsApi.get(tripId))
    } catch (reason) {
      setError(readableError(reason, 'Не удалось получить путешествие.'))
    } finally {
      setBusy(false)
    }
  }, [tripId])
  const loadBudget = useCallback(async () => {
    try {
      setBudget(await tripsApi.budget(tripId))
      setBudgetStatus('loaded')
    } catch (reason) {
      setBudgetError(readableError(reason, 'Не удалось получить бюджет поездки.'))
      setBudgetStatus('error')
    }
  }, [tripId])
  const retryTrip = () => {
    setBusy(true)
    setError('')
    loadTrip()
  }
  const retryBudget = () => {
    setBudgetError('')
    setBudgetStatus('idle')
    loadBudget()
  }

  useEffect(() => {
    loadTrip()
  }, [loadTrip])
  useEffect(() => {
    if (activeTab === 'budget') loadBudget()
  }, [activeTab, loadBudget])

  const days = useMemo(
    () => [...(trip?.days || [])].sort((a, b) => (a.dayNumber || 0) - (b.dayNumber || 0)),
    [trip],
  )
  const allItems = useMemo(
    () => days.flatMap((day) => (day.items || []).map((item) => ({ ...item, day }))),
    [days],
  )
  const tab = tabs.some(([key]) => key === activeTab) ? activeTab : 'overview'

  const removeTrip = async () => {
    setShowDelete(false)
    try {
      await tripsApi.remove(tripId)
      navigate('/app/trips')
    } catch (reason) {
      setError(readableError(reason, 'Не удалось удалить путешествие.'))
    }
  }

  const openEdit = () => {
    setEditError('')
    setEditValues({
      title: trip.title || '',
      origin: trip.origin || '',
      destination: trip.destination || '',
      startDate: trip.startDate || '',
      endDate: trip.endDate || '',
      budget: trip.budget ?? '',
      currency: trip.currency || 'RUB',
      adults: trip.adults ?? 1,
      children: trip.children ?? 0,
      tourismType: trip.tourismType || '',
      transportType: trip.transportType || '',
      guideRequired: Boolean(trip.guideRequired),
    })
    setShowEdit(true)
  }

  const saveEdit = async (event) => {
    event.preventDefault()
    setEditBusy(true)
    setEditError('')
    try {
      const saved = await tripsApi.update(tripId, {
        ...editValues,
        budget: Number(editValues.budget),
        adults: Number(editValues.adults),
        children: Number(editValues.children),
      })
      setTrip(saved)
      setShowEdit(false)
    } catch (reason) {
      setEditError(readableError(reason, 'Не удалось обновить путешествие.'))
    } finally {
      setEditBusy(false)
    }
  }

  if (busy) return <LoadingState>Открываем путешествие…</LoadingState>
  if (error && !trip) return <ErrorNotice message={error} onRetry={retryTrip} />
  if (!trip) return null

  return (
    <section className="trip-workspace">
      <div className="trip-cover">
        <div className="trip-cover__art" />
        <div className="trip-cover__content">
          <Link to="/app/trips" className="back-link">
            ← Мои путешествия
          </Link>
          <span className="eyebrow">Рабочее пространство поездки</span>
          <h1>{trip.title || trip.destination || 'Моё путешествие'}</h1>
          <p>
            {trip.origin || '—'} <Icon name="arrow" size={17} />{' '}
            {trip.destination || 'Направление не указано'}
          </p>
          <div className="trip-cover__meta">
            <span>
              <Icon name="trip" size={17} /> {displayDate(trip.startDate)}
              {trip.endDate ? ` — ${displayDate(trip.endDate)}` : ''}
            </span>
            <span>
              {trip.adults ?? '—'} взрослых{trip.children ? ` · ${trip.children} детей` : ''}
            </span>
            <span>{money(trip.budget, trip.currency || 'RUB')}</span>
          </div>
          <div className="trip-cover__actions">
            <Link
              className="button button--primary button--small"
              to={`/app/misha?tripId=${encodeURIComponent(trip.id)}`}
            >
              <Icon name="chat" size={15} /> Спросить Мишу
            </Link>
            <button className="button button--outline button--small" onClick={openEdit}>
              <Icon name="edit" size={14} /> Изменить параметры
            </button>
            <button
              className="button button--outline button--small"
              onClick={() => setShowDelete(true)}
            >
              Удалить поездку
            </button>
          </div>
        </div>
      </div>
      {error && <ErrorNotice message={error} onRetry={retryTrip} />}
      <nav className="trip-tabs" aria-label="Разделы путешествия">
        {tabs.map(([key, label]) => (
          <Link
            key={key}
            className={tab === key ? 'is-active' : ''}
            to={`/app/trips/${tripId}/${key}`}
          >
            {label}
          </Link>
        ))}
      </nav>
      <div className="trip-tab-content">
        {tab === 'overview' && (
          <Overview
            trip={trip}
            days={days}
            budget={budget}
            onLoadBudget={loadBudget}
            budgetBusy={budgetStatus === 'idle'}
          />
        )}
        {tab === 'route' && <RouteTab days={days} />}
        {tab === 'budget' && (
          <BudgetTab
            budget={budget}
            busy={budgetStatus === 'idle'}
            error={budgetError}
            onRetry={retryBudget}
          />
        )}
        {categories[tab] && <CategoryTab tab={tab} items={allItems} />}
        {tab === 'documents' && (
          <EmptyNotice title="Документы путешествия">
            В просмотренных Backend controllers нет API для загрузки и хранения документов.
            Документы нельзя сохранить до появления серверного endpoint.
          </EmptyNotice>
        )}
      </div>
      {showDelete && (
        <div
          className="modal-scrim"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setShowDelete(false)
          }}
        >
          <section
            className="confirm-modal card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-trip-title"
          >
            <span className="empty-notice__icon">
              <Icon name="alert" />
            </span>
            <h2 id="delete-trip-title">Удалить путешествие?</h2>
            <p>Действие удалит запись через Backend и не может быть отменено.</p>
            <div>
              <button
                className="button button--outline button--small"
                onClick={() => setShowDelete(false)}
              >
                Отмена
              </button>
              <button className="button button--danger button--small" onClick={removeTrip}>
                Удалить
              </button>
            </div>
          </section>
        </div>
      )}
      {showEdit && editValues && (
        <div
          className="modal-scrim"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setShowEdit(false)
          }}
        >
          <form
            className="trip-edit-modal card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-trip-title"
            onSubmit={saveEdit}
          >
            <span className="eyebrow">Параметры поездки</span>
            <h2 id="edit-trip-title">Редактировать путешествие</h2>
            {editError && <ErrorNotice message={editError} />}
            <div className="trip-edit-grid">
              <label>
                Название
                <input
                  value={editValues.title}
                  onChange={(event) => setEditValues({ ...editValues, title: event.target.value })}
                />
              </label>
              <label>
                Откуда
                <input
                  required
                  value={editValues.origin}
                  onChange={(event) => setEditValues({ ...editValues, origin: event.target.value })}
                />
              </label>
              <label>
                Куда
                <input
                  required
                  value={editValues.destination}
                  onChange={(event) =>
                    setEditValues({ ...editValues, destination: event.target.value })
                  }
                />
              </label>
              <label>
                Начало
                <input
                  type="date"
                  required
                  value={editValues.startDate}
                  onChange={(event) =>
                    setEditValues({ ...editValues, startDate: event.target.value })
                  }
                />
              </label>
              <label>
                Окончание
                <input
                  type="date"
                  required
                  value={editValues.endDate}
                  onChange={(event) =>
                    setEditValues({ ...editValues, endDate: event.target.value })
                  }
                />
              </label>
              <label>
                Бюджет, ₽
                <input
                  type="number"
                  min="0"
                  step="100"
                  required
                  value={editValues.budget}
                  onChange={(event) => setEditValues({ ...editValues, budget: event.target.value })}
                />
              </label>
              <label>
                Взрослые
                <input
                  type="number"
                  min="1"
                  required
                  value={editValues.adults}
                  onChange={(event) => setEditValues({ ...editValues, adults: event.target.value })}
                />
              </label>
              <label>
                Дети
                <input
                  type="number"
                  min="0"
                  required
                  value={editValues.children}
                  onChange={(event) =>
                    setEditValues({ ...editValues, children: event.target.value })
                  }
                />
              </label>
              <label>
                Виды путешествия
                <input
                  value={editValues.tourismType}
                  onChange={(event) =>
                    setEditValues({ ...editValues, tourismType: event.target.value })
                  }
                />
              </label>
              <label>
                Транспорт
                <input
                  value={editValues.transportType}
                  onChange={(event) =>
                    setEditValues({ ...editValues, transportType: event.target.value })
                  }
                />
              </label>
              <label className="trip-edit-guide">
                <input
                  type="checkbox"
                  checked={editValues.guideRequired}
                  onChange={(event) =>
                    setEditValues({ ...editValues, guideRequired: event.target.checked })
                  }
                />{' '}
                Нужен гид
              </label>
            </div>
            <div className="confirm-modal__actions">
              <button
                type="button"
                className="button button--outline button--small"
                onClick={() => setShowEdit(false)}
              >
                Отмена
              </button>
              <button className="button button--primary button--small" disabled={editBusy}>
                {editBusy ? 'Сохраняем…' : 'Сохранить изменения'}
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  )
}

function Overview({ trip, days, budget, onLoadBudget, budgetBusy }) {
  return (
    <>
      <div className="overview-stats">
        <article className="card">
          <small>Направление</small>
          <b>{trip.destination || 'Не указано'}</b>
        </article>
        <article className="card">
          <small>Даты</small>
          <b>
            {trip.startDate
              ? `${displayDate(trip.startDate)}${trip.endDate ? ` — ${displayDate(trip.endDate)}` : ''}`
              : 'Не указаны'}
          </b>
        </article>
        <article className="card">
          <small>Путешественники</small>
          <b>
            {trip.adults ?? '—'} взрослых{trip.children ? `, ${trip.children} детей` : ''}
          </b>
        </article>
        <article className="card">
          <small>Бюджет</small>
          <b>
            {budget
              ? money(budget.totalCost, trip.currency || 'RUB')
              : money(trip.budget, trip.currency || 'RUB')}
          </b>
          {!budget && (
            <button className="text-button" onClick={onLoadBudget} disabled={budgetBusy}>
              {budgetBusy ? 'Считаем…' : 'Обновить расчёт'}
            </button>
          )}
        </article>
      </div>
      <div className="trip-content-heading">
        <div>
          <h2>Программа поездки</h2>
          <p>Данные по дням из сохранённого Trip в Backend</p>
        </div>
        <Link className="button button--outline button--small" to={`/app/trips/${trip.id}/route`}>
          Открыть маршрут <Icon name="arrow" size={15} />
        </Link>
      </div>
      {days.length ? (
        <div className="day-list">
          {days.map((day) => (
            <article className="day-card card" key={day.id || day.dayNumber}>
              <div className="day-card__heading">
                <span>День {day.dayNumber || '—'}</span>
                <b>{displayDate(day.date)}</b>
              </div>
              {day.items?.length ? (
                day.items.map((item) => (
                  <div className="day-item" key={item.id}>
                    <time>{item.startTime || 'Время не указано'}</time>
                    <span className="day-item__dot" />
                    <div>
                      <b>{itemName(item)}</b>
                      <p>
                        {item.notes || 'Описание не передано Backend'}
                        {item.durationMinutes ? ` · ${item.durationMinutes} мин.` : ''}
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="muted-caption">
                  Для этого дня Backend пока не вернул пункты маршрута.
                </p>
              )}
            </article>
          ))}
        </div>
      ) : (
        <EmptyNotice title="Маршрут ещё не сформирован">
          В ответе Backend нет дней поездки. MRT сейчас умеет выбрать регион, но не возвращает
          готовый маршрут для сохранения.
        </EmptyNotice>
      )}
      <div className="trip-content-heading">
        <div>
          <h2>Состояние поездки</h2>
          <p>Доступные сведения из Backend</p>
        </div>
      </div>
      <div className="backend-capabilities card">
        <span>
          <Icon name="check" /> Поездка сохранена
        </span>
        <span>
          <Icon name="alert" /> Статус бронирований не предоставлен API
        </span>
        <span>
          <Icon name="alert" /> Проверенные цены услуг не предоставлены API
        </span>
        <span>
          <Icon name="alert" /> Загрузка документов не предоставлена API
        </span>
      </div>
    </>
  )
}

function RouteTab({ days }) {
  return (
    <div className="route-layout">
      <section>
        <div className="trip-content-heading">
          <div>
            <h2>Маршрут по дням</h2>
            <p>Пункты показаны в том виде, в котором их вернул Backend</p>
          </div>
        </div>
        {days.length ? (
          <div className="day-list">
            {days.map((day) => (
              <article className="day-card card" key={day.id || day.dayNumber}>
                <div className="day-card__heading">
                  <span>День {day.dayNumber || '—'}</span>
                  <b>{displayDate(day.date)}</b>
                </div>
                {day.items?.length ? (
                  day.items.map((item) => (
                    <div className="day-item" key={item.id}>
                      <time>{item.startTime || '—'}</time>
                      <span className="day-item__dot" />
                      <div>
                        <b>{itemName(item)}</b>
                        <p>
                          {item.notes || 'Описание не передано'}
                          {item.durationMinutes ? ` · ${item.durationMinutes} мин.` : ''}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="muted-caption">Пунктов пока нет.</p>
                )}
              </article>
            ))}
          </div>
        ) : (
          <EmptyNotice title="Пока нет маршрута">
            Дни и точки не были возвращены Backend. MRT endpoint для генерации маршрута отсутствует.
          </EmptyNotice>
        )}
      </section>
      <aside className="map-placeholder card">
        <span className="map-placeholder__icon">
          <Icon name="pin" size={27} />
        </span>
        <h3>Карта поездки</h3>
        <p>
          Сохранённый Trip не содержит координаты или геометрию маршрута. Мы не рисуем фиктивный
          путь.
        </p>
      </aside>
    </div>
  )
}

function CategoryTab({ tab, items }) {
  const definition = categories[tab]
  const filtered = items.filter((item) =>
    definition.keywords.some((word) => itemCategory(item).includes(word)),
  )
  return (
    <section>
      <div className="trip-content-heading">
        <div>
          <h2>{definition.title}</h2>
          <p>Сохранённые пункты маршрута и данные доступных сервисов</p>
        </div>
      </div>
      {filtered.length ? (
        <div className="resource-list">
          {filtered.map((item) => (
            <article className="resource-card card" key={`${item.day?.id}-${item.id}`}>
              <span className="resource-card__icon">
                <Icon
                  name={
                    tab === 'hotels'
                      ? 'bed'
                      : tab === 'restaurants'
                        ? 'food'
                        : tab === 'tickets'
                          ? 'ticket'
                          : 'landmark'
                  }
                />
              </span>
              <div>
                <b>{itemName(item)}</b>
                <p>{item.notes || 'Дополнительные сведения отсутствуют в ответе Backend.'}</p>
                <small>
                  День {item.day.dayNumber || '—'} · {item.startTime || 'Время не указано'}
                </small>
              </div>
              <span className="resource-price">
                {item.estimatedCost == null ? 'Цена не указана' : money(item.estimatedCost)}
              </span>
            </article>
          ))}
        </div>
      ) : (
        <EmptyNotice
          title={
            filtered.length
              ? `Сохранённые данные: ${definition.title}`
              : `Пока нет данных: ${definition.title}`
          }
        >
          Backend не возвращает отдельный каталог, актуальные предложения, доступность, рейтинги или
          ссылки для покупки и бронирования. Если данные появятся в сохранённом маршруте, они
          отобразятся здесь.
        </EmptyNotice>
      )}
    </section>
  )
}

function BudgetTab({ budget, busy, error, onRetry }) {
  if (busy) return <LoadingState>Запрашиваем расчёт бюджета…</LoadingState>
  if (error) return <ErrorNotice message={error} onRetry={onRetry} />
  if (!budget)
    return (
      <EmptyNotice title="Расчёт бюджета недоступен">
        Backend не вернул сводку. Неизвестные суммы остаются неизвестными и не подменяются нулями.
      </EmptyNotice>
    )
  return (
    <section className="budget-view">
      <div className="trip-content-heading">
        <div>
          <h2>Бюджет путешествия</h2>
          <p>Сводка, рассчитанная Backend</p>
        </div>
      </div>
      <article className="budget-total card">
        <span>Общая сумма</span>
        <b>{money(budget.totalCost)}</b>
        <small>
          {budget.isOverBudget == null
            ? 'Сравнение с лимитом не предоставлено'
            : budget.isOverBudget
              ? 'Сумма превышает лимит'
              : 'В пределах лимита Backend'}
        </small>
      </article>
      <div className="budget-lines card">
        {Object.entries(budget.costByCategory || {}).map(([category, amount]) => (
          <div key={category}>
            <span>{category}</span>
            <b>{money(amount)}</b>
          </div>
        ))}
        {budget.budgetLimit != null && (
          <div>
            <span>Установленный лимит</span>
            <b>{money(budget.budgetLimit)}</b>
          </div>
        )}
        {budget.remainingBudget != null && (
          <div>
            <span>Остаток</span>
            <b>{money(budget.remainingBudget)}</b>
          </div>
        )}
        {!Object.keys(budget.costByCategory || {}).length && (
          <p className="muted-caption">Backend не вернул разбивку по категориям.</p>
        )}
      </div>
    </section>
  )
}
