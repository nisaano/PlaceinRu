import { useState } from 'react'
import { useAuth } from '../../auth/AuthContext'
import { ErrorNotice, LoadingState } from '../../components/common/Feedback'
import { Icon } from '../../components/common/Icon'
import './ProfilePage.css'

export function ProfilePage() {
  const { user, loading, logout } = useAuth()
  const [message, setMessage] = useState('')
  if (loading) return <LoadingState>Загружаем профиль…</LoadingState>
  if (!user) return <ErrorNotice message="Профиль недоступен. Войдите в аккаунт снова." />
  return (
    <section className="profile-page">
      <div className="page-header">
        <div>
          <span className="eyebrow">Настройки аккаунта</span>
          <h1>Профиль</h1>
          <p>Данные текущего пользователя из Backend.</p>
        </div>
      </div>
      <article className="profile-card card">
        <span className="profile-card__avatar">
          {(user.name || user.email || 'П').slice(0, 1).toUpperCase()}
        </span>
        <div className="profile-fields">
          <label>
            Имя
            <input readOnly value={user.name || 'Не указано'} />
          </label>
          <label>
            Email
            <input readOnly value={user.email || 'Не указан'} />
          </label>
          <label>
            ID пользователя
            <input readOnly value={user.id ?? 'Не указан'} />
          </label>
          <label>
            Дата регистрации
            <input
              readOnly
              value={
                user.createdAt ? new Date(user.createdAt).toLocaleDateString('ru-RU') : 'Не указана'
              }
            />
          </label>
        </div>
        <div className="notice">
          <Icon name="alert" size={18} />
          <p>
            Backend API просмотра профиля работает. Отдельный endpoint обновления профиля не найден.
          </p>
        </div>
        <button
          className="button button--outline button--small"
          onClick={() => {
            logout()
            setMessage('Вы вышли из аккаунта.')
          }}
        >
          Выйти
        </button>
        {message && (
          <p role="status" className="profile-status">
            {message}
          </p>
        )}
      </article>
    </section>
  )
}
