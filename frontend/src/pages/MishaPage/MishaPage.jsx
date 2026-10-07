import { useCallback, useEffect, useMemo, useState } from 'react'
import mascot from '../../assets/figma/assistant-background.png'
import { mrtApi } from '../../api/mrt'
import { tripsApi } from '../../api/trips'
import { readableError } from '../../api/client'
import { Icon } from '../../components/common/Icon'
import { ErrorNotice, LoadingState } from '../../components/common/Feedback'
import { RouterProvider } from '../../router/Router'
import './MishaPage.css'

const interestsList = [
  'Природа',
  'Горы',
  'Культура',
  'Активный отдых',
  'Пляж',
  'Пикник',
  'Гастрономия',
  'Семейный отдых',
]
const typesToInterests = {
  Природа: 'природа',
  Горы: 'горы',
  Культура: 'культура',
  'Активный отдых': 'активный',
  Пляж: 'море',
  Пикник: 'природа',
  Гастрономия: 'гастрономия',
  'Семейный отдых': 'семейный',
}
const requestId = () => crypto.randomUUID()

export function MishaPage({ tripId = null }) {
  const { navigate } = RouterProvider.useRouter()
  const [session, setSession] = useState(null)
  const [screen, setScreen] = useState('welcome')
  const [busy, setBusy] = useState(true)
  const [operation, setOperation] = useState('')
  const [error, setError] = useState('')
  const [chatText, setChatText] = useState(
    () => sessionStorage.getItem('placeinru.mishaPrompt') || '',
  )
  const [selectedRegion, setSelectedRegion] = useState(null)
  const [demoCandidates, setDemoCandidates] = useState([])
  const [demoBusy, setDemoBusy] = useState(false)
  const [form, setForm] = useState({
    date: '',
    duration: '5',
    origin: '',
    adults: '2',
    childrenCount: '0',
    interests: [],
    pace: 'balanced',
    transports: ['TRAIN', 'FLIGHT'],
    guide: false,
    budget: '',
  })
  const messages = session?.messages || []

  const loadSession = useCallback(async () => {
    try {
      const savedId = sessionStorage.getItem('placeinru.mrtSession')
      const state = savedId ? await mrtApi.getSession(savedId).catch(() => null) : null
      const next = state || (await mrtApi.createSession())
      sessionStorage.setItem('placeinru.mrtSession', next.session_id)
      setSession(next)
    } catch (reason) {
      setError(readableError(reason, 'Не удалось открыть помощника Мишу.'))
    } finally {
      setBusy(false)
    }
  }, [])

  useEffect(() => {
    loadSession()
  }, [loadSession])
  useEffect(() => {
    sessionStorage.removeItem('placeinru.mishaPrompt')
  }, [])

  const retrySession = () => {
    setBusy(true)
    setError('')
    loadSession()
  }

  const setField = (key, value) => setForm((current) => ({ ...current, [key]: value }))
  const toggleListValue = (key, value) =>
    setForm((current) => ({
      ...current,
      [key]: current[key].includes(value)
        ? current[key].filter((item) => item !== value)
        : [...current[key], value],
    }))
  const recommendations = session?.recommendations?.options || []

  const submitParameters = async (event) => {
    event.preventDefault()
    if (!session) return
    setBusy(true)
    setError('')
    try {
      const updates = {
        mode: 'DISCOVER',
        origin: form.origin.trim(),
        'dates.start_date': form.date,
        'dates.duration_days': Number(form.duration),
        'party.adults': Number(form.adults),
        'party.children_count': Number(form.childrenCount),
        interests: form.interests.map((interest) => typesToInterests[interest]).filter(Boolean),
        'format.pace': form.pace,
        'transport.allowed_modes': form.transports,
        'guide.required': form.guide,
        'budget.amount_minor': Math.round(Number(form.budget) * 100),
        'budget.basis': 'group',
        'budget.period': 'trip',
      }
      const result = await mrtApi.updateTrip(session.session_id, {
        request_id: requestId(),
        expected_state_version: session.state_version,
        updates,
      })
      setSession(result.state)
      setSelectedRegion(null)
      setScreen('results')
    } catch (reason) {
      if (reason.status === 409) await reloadCurrentSession()
      setError(readableError(reason, 'Не получилось отправить параметры Мише.'))
    } finally {
      setBusy(false)
    }
  }

  const reloadCurrentSession = async () => {
    if (!session?.session_id) return
    try {
      setSession(await mrtApi.getSession(session.session_id))
    } catch {
      /* Ошибка основного запроса будет показана ниже. */
    }
  }

  const selectRegion = async (region) => {
    setOperation(region.region_id)
    setError('')
    try {
      const result = await mrtApi.selectRegion(session.session_id, {
        request_id: requestId(),
        expected_state_version: session.state_version,
        region_id: region.region_id,
        catalog_snapshot_id: session.recommendations.catalog_snapshot_id,
      })
      setSession(result.state)
      setSelectedRegion(region)
      setDemoCandidates([])
      setScreen('selected')
    } catch (reason) {
      if (reason.status === 409) await reloadCurrentSession()
      setError(readableError(reason, 'Не получилось выбрать это направление. Обновите варианты.'))
    } finally {
      setOperation('')
    }
  }

  const loadDemoCandidates = async () => {
    if (!selectedRegion) return
    setDemoBusy(true)
    setError('')
    try {
      const result = await mrtApi.candidates({
        region_id: selectedRegion.region_id,
        data_mode: 'fixture',
      })
      setDemoCandidates(result.candidates || [])
      if (!result.candidates?.length) setError('Для этого региона MRT не вернул демо-объекты.')
    } catch (reason) {
      setError(readableError(reason, 'Демо-каталог временно недоступен.'))
    } finally {
      setDemoBusy(false)
    }
  }

  const createTrip = async () => {
    if (!session?.trip || !selectedRegion) return
    setOperation('save')
    setError('')
    const trip = session.trip
    try {
      const created = await tripsApi.create({
        title: selectedRegion.name,
        origin: trip.origin,
        destination: selectedRegion.name,
        startDate: trip.dates.start_date,
        endDate: trip.dates.end_date,
        budget: Number(trip.budget.amount_minor) / 100,
        currency: trip.budget.currency || 'RUB',
        adults: trip.party.adults,
        children: trip.party.children_count,
        tourismType: trip.interests.join(', '),
        transportType: trip.transport.allowed_modes.join(', '),
        guideRequired: Boolean(trip.guide.required),
      })
      navigate(`/app/trips/${created.id}/overview`)
    } catch (reason) {
      setError(readableError(reason, 'Не удалось сохранить поездку в аккаунт.'))
    } finally {
      setOperation('')
    }
  }

  const sendMessage = async (event) => {
    event.preventDefault()
    if (!chatText.trim() || !session) return
    setOperation('chat')
    setError('')
    try {
      const result = await mrtApi.turn(session.session_id, {
        request_id: requestId(),
        expected_state_version: session.state_version,
        message: chatText.trim(),
      })
      setSession(result.state)
      setChatText('')
      if (result.options?.length) setScreen('results')
    } catch (reason) {
      if (reason.status === 409) await reloadCurrentSession()
      setError(readableError(reason, 'Миша пока не отвечает. Попробуйте ещё раз.'))
    } finally {
      setOperation('')
    }
  }

  const startForm = () => {
    setScreen('form')
    setSelectedRegion(null)
  }
  const formattedBudget = useMemo(
    () => (form.budget ? new Intl.NumberFormat('ru-RU').format(Number(form.budget)) : ''),
    [form.budget],
  )

  if (busy && !session)
    return (
      <section className="misha-page">
        <LoadingState>Миша готовится к разговору…</LoadingState>
      </section>
    )

  return (
    <section className="misha-page">
      <div className="page-header misha-page__header">
        <div>
          <span className="eyebrow">Планирование поездки</span>
          <h1>Миша — твой помощник</h1>
          <p>Соберём параметры поездки и подберём доступное направление.</p>
        </div>
        {tripId && <span className="trip-context">Путешествие №{tripId}</span>}
      </div>
      {error && <ErrorNotice message={error} onRetry={retrySession} />}
      {!session && !busy && (
        <div className="card">
          <p className="missing-config">
            Проверьте адрес MRT API в `VITE_MRT_URL` и запустите сервис, затем повторите попытку.
          </p>
          <button className="button button--outline button--small" onClick={retrySession}>
            Повторить
          </button>
        </div>
      )}

      {session && tripId && (
        <div className="notice misha-trip-warning">
          <Icon name="alert" size={18} />
          <p>
            Открыто путешествие №{tripId}. Текущий MRT контракт не связывает сессию с сохранённым
            Trip и не применяет чат-изменения к Backend; здесь доступен отдельный диалог.
          </p>
        </div>
      )}
      {session && (
        <div className="misha-workspace">
          <div className="misha-thread card">
            <div className="misha-thread__top">
              <span className="misha-avatar">
                <img src={mascot} alt="Миша, помощник PlaceinRU" />
              </span>
              <div>
                <b>Миша</b>
                <small>помощник в путешествиях по России</small>
              </div>
              <span className="online-dot" aria-label="MRT-сессия открыта" />
            </div>
            <div className="misha-thread__messages" aria-live="polite">
              <article className="message message--assistant">
                <b>Миша</b>
                <p>
                  Привет! Я Миша, твой помощник в путешествиях по России. Помогу уточнить планы и
                  подобрать направление.
                </p>
              </article>
              {messages.map((message, index) => (
                <article
                  key={`${index}-${message.role}`}
                  className={`message message--${message.role}`}
                >
                  <b>{message.role === 'assistant' ? 'Миша' : 'Вы'}</b>
                  <p>{message.text}</p>
                </article>
              ))}
              {operation === 'chat' && (
                <div className="message message--assistant">
                  <span className="spinner" />
                  Миша думает…
                </div>
              )}
            </div>
            <form className="misha-chat-input" onSubmit={sendMessage}>
              <input
                value={chatText}
                onChange={(event) => setChatText(event.target.value)}
                placeholder="Напишите, куда хотите поехать…"
                aria-label="Сообщение Мише"
              />
              <button
                disabled={!chatText.trim() || operation === 'chat'}
                aria-label="Отправить сообщение"
              >
                <Icon name="send" />
              </button>
            </form>
          </div>

          <div className="misha-side-panel">
            {screen === 'welcome' && (
              <div className="misha-welcome card">
                <div className="misha-welcome__art">
                  <img src={mascot} alt="Миша с картой путешествий" />
                </div>
                <span className="eyebrow">С чего начнём?</span>
                <h2>Ваше путешествие начинается с идеи</h2>
                <p>
                  Расскажите, когда и откуда поедете, что вам интересно — Миша сверится с каталогом
                  направлений.
                </p>
                <div className="misha-actions">
                  <button className="button button--primary" onClick={startForm}>
                    Собрать маршрут <Icon name="arrow" size={16} />
                  </button>
                  <button className="button button--outline" onClick={() => navigate('/app/trips')}>
                    Мои маршруты <Icon name="trip" size={17} />
                  </button>
                  <button
                    className="button button--soft"
                    onClick={() => document.querySelector('.misha-chat-input input')?.focus()}
                  >
                    <Icon name="pin" size={17} /> Спросить о месте
                  </button>
                </div>
                <p className="misha-capability-note">
                  Сейчас Миша подбирает регионы по параметрам. Проверенные цены, бронирование и
                  автоматический маршрут ещё не подключены.
                </p>
              </div>
            )}

            {screen === 'form' && (
              <form className="misha-form card" onSubmit={submitParameters}>
                <div className="misha-form__heading">
                  <span className="eyebrow">Параметры путешествия</span>
                  <h2>Расскажите о планах</h2>
                  <p>Эти сведения Миша передаст сервису подбора.</p>
                </div>
                <label>
                  Когда планируете поездку?
                  <input
                    type="date"
                    min={new Date().toISOString().slice(0, 10)}
                    required
                    value={form.date}
                    onChange={(event) => setField('date', event.target.value)}
                  />
                </label>
                <div className="form-row">
                  <label>
                    На сколько дней?
                    <input
                      type="number"
                      min="1"
                      max="90"
                      required
                      value={form.duration}
                      onChange={(event) => setField('duration', event.target.value)}
                    />
                  </label>
                  <label>
                    Взрослых
                    <input
                      type="number"
                      min="1"
                      max="30"
                      required
                      value={form.adults}
                      onChange={(event) => setField('adults', event.target.value)}
                    />
                  </label>
                </div>
                <label>
                  Детей
                  <input
                    type="number"
                    min="0"
                    max="20"
                    required
                    value={form.childrenCount}
                    onChange={(event) => setField('childrenCount', event.target.value)}
                  />
                </label>
                <label>
                  Откуда отправляетесь?
                  <input
                    required
                    maxLength="120"
                    placeholder="Например, Москва"
                    value={form.origin}
                    onChange={(event) => setField('origin', event.target.value)}
                  />
                </label>
                <label>
                  Бюджет на всю поездку, ₽
                  <input
                    type="number"
                    min="0"
                    step="1000"
                    required
                    value={form.budget}
                    onChange={(event) => setField('budget', event.target.value)}
                    placeholder="Укажите общий бюджет"
                  />
                </label>
                <fieldset>
                  <legend>Что хотите делать?</legend>
                  <div className="interest-grid">
                    {interestsList.map((interest) => (
                      <button
                        className={form.interests.includes(interest) ? 'is-selected' : ''}
                        type="button"
                        key={interest}
                        onClick={() => toggleListValue('interests', interest)}
                      >
                        {interest}
                      </button>
                    ))}
                  </div>
                </fieldset>
                <label>
                  Темп поездки
                  <select
                    value={form.pace}
                    onChange={(event) => setField('pace', event.target.value)}
                  >
                    <option value="relaxed">Спокойный</option>
                    <option value="balanced">Умеренный</option>
                    <option value="active">Активный</option>
                  </select>
                </label>
                <fieldset>
                  <legend>Транспорт</legend>
                  <div className="interest-grid">
                    {[
                      ['TRAIN', 'Поезд'],
                      ['FLIGHT', 'Самолёт'],
                      ['CAR', 'Автомобиль'],
                      ['BUS', 'Автобус'],
                    ].map(([key, label]) => (
                      <button
                        className={form.transports.includes(key) ? 'is-selected' : ''}
                        type="button"
                        key={key}
                        onClick={() => toggleListValue('transports', key)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </fieldset>
                <label className="toggle-row">
                  <span>Нужен гид?</span>
                  <input
                    type="checkbox"
                    checked={form.guide}
                    onChange={(event) => setField('guide', event.target.checked)}
                  />
                </label>
                <div className="misha-form__footer">
                  <button
                    type="button"
                    className="button button--outline button--small"
                    onClick={() => setScreen('welcome')}
                  >
                    Назад
                  </button>
                  <button
                    className="button button--primary"
                    disabled={busy || form.interests.length === 0}
                  >
                    {busy ? 'Передаём Мише…' : 'Подобрать направление'}{' '}
                    <Icon name="arrow" size={16} />
                  </button>
                </div>
              </form>
            )}

            {screen === 'results' && (
              <div className="misha-results card">
                <span className="eyebrow">Ответ каталога MRT</span>
                <h2>{recommendations.length ? 'Подходящие направления' : 'Уточняем параметры'}</h2>
                <p>
                  {session.recommendations?.warnings?.[0] ||
                    (recommendations.length
                      ? 'Варианты рассчитаны по текущему региональному каталогу.'
                      : `Миша просит уточнить: ${session.missing_parameters?.join(', ') || 'другие параметры поездки'}.`)}
                </p>
                {recommendations.map((region) => (
                  <article className="recommendation-card" key={region.region_id}>
                    <div className="recommendation-card__top">
                      <span className="recommendation-pin">
                        <Icon name="pin" size={19} />
                      </span>
                      <div>
                        <h3>{region.name}</h3>
                        <p>{region.description}</p>
                      </div>
                    </div>
                    <div className="recommendation-reasons">
                      {region.reasons?.map((reason) => (
                        <span key={reason}>
                          <Icon name="check" size={13} />
                          {reason}
                        </span>
                      ))}
                    </div>
                    <p className="unknown-price">Стоимость и доступность услуг не рассчитаны</p>
                    <button
                      className="button button--primary button--small"
                      disabled={Boolean(operation)}
                      onClick={() => selectRegion(region)}
                    >
                      {operation === region.region_id ? 'Выбираем…' : 'Выбрать направление'}{' '}
                      <Icon name="arrow" size={15} />
                    </button>
                  </article>
                ))}
                {!recommendations.length && (
                  <button className="button button--outline button--small" onClick={startForm}>
                    Изменить параметры
                  </button>
                )}
              </div>
            )}

            {screen === 'selected' && selectedRegion && (
              <div className="selected-region card">
                <span className="eyebrow">Направление выбрано в MRT</span>
                <h2>{selectedRegion.name}</h2>
                <p>{selectedRegion.description}</p>
                <div className="selection-summary">
                  <span>
                    <small>Отправление</small>
                    <b>{session.trip.origin}</b>
                  </span>
                  <span>
                    <small>Даты</small>
                    <b>
                      {session.trip.dates.start_date} · {session.trip.dates.duration_days} дн.
                    </b>
                  </span>
                  <span>
                    <small>Бюджет пользователя</small>
                    <b>{formattedBudget} ₽</b>
                  </span>
                </div>
                <div className="notice">
                  <Icon name="alert" size={18} />
                  <p>
                    Сервис пока не возвращает предварительный маршрут, реальные цены или варианты
                    бронирования. Сохранение создаст поездку в Backend с введёнными параметрами.
                  </p>
                </div>
                {import.meta.env.VITE_ENABLE_DEMO_MODE === 'true' && (
                  <div className="demo-candidates">
                    <button
                      className="button button--outline button--small"
                      onClick={loadDemoCandidates}
                      disabled={demoBusy}
                    >
                      {demoBusy ? 'Загружаем демо-каталог…' : 'Посмотреть демо-объекты'}{' '}
                      <Icon name="arrow" size={15} />
                    </button>
                    {demoCandidates.map((candidate) => (
                      <article key={candidate.object_id}>
                        <span>ДЕМО</span>
                        <b>{candidate.name}</b>
                        <p>{candidate.description}</p>
                        <small>
                          {candidate.source.attribution} · цены и доступность не предоставлены
                        </small>
                      </article>
                    ))}
                  </div>
                )}
                <button
                  className="button button--primary"
                  onClick={createTrip}
                  disabled={operation === 'save'}
                >
                  {operation === 'save' ? 'Сохраняем…' : 'Сохранить путешествие'}{' '}
                  <Icon name="arrow" size={16} />
                </button>
                <button className="text-button" onClick={startForm}>
                  Изменить параметры
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
