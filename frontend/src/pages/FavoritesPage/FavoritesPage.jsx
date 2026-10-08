import { useCallback, useEffect, useState } from 'react'
import { mrtApi } from '../../api/mrt'
import { readableError } from '../../api/client'
import { EmptyNotice, ErrorNotice, LoadingState } from '../../components/common/Feedback'
import { Icon } from '../../components/common/Icon'
import { RouterProvider } from '../../router/Router'
import './FavoritesPage.css'

function readFavorites() {
  try {
    return JSON.parse(localStorage.getItem('placeinru.favorites') || '[]')
  } catch {
    return []
  }
}

export function FavoritesPage() {
  const { navigate } = RouterProvider.useRouter()
  const [regions, setRegions] = useState([])
  const [favorites, setFavorites] = useState(readFavorites)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const catalog = await mrtApi.catalog()
      setRegions(catalog.regions || [])
    } catch (reason) {
      setError(readableError(reason, 'Не удалось получить каталог направлений.'))
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

  const toggle = (region) => {
    setFavorites((current) => {
      const next = current.some((item) => item.region_id === region.region_id)
        ? current.filter((item) => item.region_id !== region.region_id)
        : [...current, region]
      localStorage.setItem('placeinru.favorites', JSON.stringify(next))
      return next
    })
  }

  return (
    <section className="favorites-page">
      <div className="page-header">
        <div>
          <span className="eyebrow">Сохранённое</span>
          <h1>Избранное</h1>
          <p>Отметьте интересные направления, чтобы вернуться к ним позже.</p>
        </div>
      </div>
      <div className="notice">
        <Icon name="alert" size={18} />
        <p>
          Избранное пока хранится только в этом браузере. Backend API для синхронизации избранного
          отсутствует.
        </p>
      </div>
      {error && <ErrorNotice message={error} onRetry={retryLoad} />}
      {busy ? (
        <LoadingState>Загружаем направления…</LoadingState>
      ) : favorites.length ? (
        <div className="favorite-grid">
          {favorites.map((region) => (
            <article className="favorite-card card" key={region.region_id}>
              <span className="favorite-card__pin">
                <Icon name="pin" size={20} />
              </span>
              <h2>{region.name}</h2>
              <p>{region.description}</p>
              <div className="favorite-tags">
                {region.tags?.slice(0, 4).map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
              <div className="favorite-card__actions">
                <button
                  className="button button--outline button--small"
                  onClick={() => {
                    sessionStorage.setItem('placeinru.mishaPrompt', `Хочу поехать в ${region.name}`)
                    navigate('/app/misha')
                  }}
                >
                  Обсудить с Мишей
                </button>
                <button
                  className="icon-button"
                  aria-label={`Убрать ${region.name} из избранного`}
                  onClick={() => toggle(region)}
                >
                  <Icon name="heart" size={18} />
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyNotice title="Пока ничего не сохранено">
          Избранное хранится в текущем браузере, пока для него не подключено серверное API.
        </EmptyNotice>
      )}
      {regions.length > 0 && (
        <div className="favorite-catalog">
          <div className="trip-content-heading">
            <div>
              <h2>Направления из каталога</h2>
              <p>Сохраняйте регионы, которые хотите обсудить с Мишей</p>
            </div>
          </div>
          <div className="favorite-region-list">
            {regions.map((region) => {
              const saved = favorites.some((item) => item.region_id === region.region_id)
              return (
                <button key={region.region_id} onClick={() => toggle(region)}>
                  <span>
                    <b>{region.name}</b>
                    <small>{region.description}</small>
                  </span>
                  <Icon name={saved ? 'heart' : 'plus'} size={19} />
                </button>
              )
            })}
          </div>
        </div>
      )}
    </section>
  )
}
