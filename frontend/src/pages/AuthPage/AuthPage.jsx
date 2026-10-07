import { useState } from 'react'
import { authApi } from '../../api/auth'
import { readableError } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { Icon } from '../../components/common/Icon'
import { Link } from '../../router/Router'
import authArtwork from '../../assets/figma/Mascot.png'
import './AuthPage.css'

export function AuthPage({ mode }) {
  const register = mode === 'register'
  const { acceptAuth } = useAuth()
  const [values, setValues] = useState({
    name: '',
    email: '',
    password: '',
    confirm: '',
    consent: false,
  })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (event) => {
    const { name, value, checked, type } = event.target
    setValues((current) => ({ ...current, [name]: type === 'checkbox' ? checked : value }))
    setError('')
  }

  async function submit(event) {
    event.preventDefault()
    if (register && values.password !== values.confirm) return setError('Пароли не совпадают.')
    if (register && !values.consent) return setError('Подтвердите согласие на обработку данных.')
    setBusy(true)
    setError('')
    try {
      const response = register
        ? await authApi.register({
            name: values.name.trim(),
            email: values.email.trim(),
            password: values.password,
          })
        : await authApi.login({ email: values.email.trim(), password: values.password })
      await acceptAuth(response)
      window.history.pushState({}, '', '/app')
      window.dispatchEvent(new PopStateEvent('popstate'))
    } catch (reason) {
      setError(readableError(reason, 'Не удалось войти. Проверьте данные и повторите попытку.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth-shell">
      <Link className="auth-back" to="/">
        ← На главную
      </Link>
      <div className="auth-layout">
        <section className="auth-card">
          <div className="auth-brand">
            <span className="brand-pin">
              <Icon name="pin" size={21} />
            </span>
            <b>PlaceinRu</b>
          </div>
          <span className="eyebrow">Твои путешествия начинаются здесь</span>
          <h1>{register ? 'Добро пожаловать!' : 'С возвращением!'}</h1>
          <p className="auth-lead">
            {register
              ? 'Создайте аккаунт, чтобы планировать свои путешествия'
              : 'Войдите, чтобы продолжить планирование поездки'}
          </p>
          <div className="auth-tabs">
            <Link className={!register ? 'is-active' : ''} to="/login">
              Войти
            </Link>
            <Link className={register ? 'is-active' : ''} to="/register">
              Регистрация
            </Link>
          </div>
          <form className="auth-form" onSubmit={submit}>
            {register && (
              <label>
                Имя
                <input
                  name="name"
                  autoComplete="name"
                  minLength={3}
                  maxLength={10}
                  required
                  value={values.name}
                  onChange={update}
                  placeholder="Как к вам обращаться?"
                />
              </label>
            )}
            <label>
              Email
              <input
                name="email"
                type="email"
                autoComplete="email"
                required
                value={values.email}
                onChange={update}
                placeholder="name@example.ru"
              />
            </label>
            <label>
              Пароль
              <div className="password-control">
                <input
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete={register ? 'new-password' : 'current-password'}
                  minLength={register ? 6 : undefined}
                  maxLength={register ? 20 : undefined}
                  required
                  value={values.password}
                  onChange={update}
                  placeholder="Введите пароль"
                />
                <button
                  type="button"
                  aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? 'Скрыть' : 'Показать'}
                </button>
              </div>
            </label>
            {register && (
              <label>
                Повторите пароль
                <input
                  name="confirm"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  required
                  value={values.confirm}
                  onChange={update}
                  placeholder="Введите пароль ещё раз"
                />
              </label>
            )}
            {register && (
              <label className="auth-consent">
                <input name="consent" type="checkbox" checked={values.consent} onChange={update} />
                <span>
                  Я согласен(на) с условиями использования и обработкой персональных данных
                </span>
              </label>
            )}
            {error && (
              <p className="auth-error" role="alert">
                {error}
              </p>
            )}
            <button className="button button--primary auth-submit" disabled={busy}>
              {busy ? 'Подождите…' : register ? 'Зарегистрироваться' : 'Войти'}{' '}
              <Icon name="arrow" size={18} />
            </button>
          </form>
          <p className="auth-switch">
            {register ? 'Уже есть аккаунт?' : 'Нет аккаунта?'}{' '}
            <Link to={register ? '/login' : '/register'}>
              {register ? 'Войти' : 'Зарегистрироваться'}
            </Link>
          </p>
        </section>
        <aside className="auth-illustration">
          <div className="auth-illustration__caption">
            <span className="eyebrow">PlaceinRu</span>
            <p>Найдём вдохновение и соберём путешествие вместе с Мишей.</p>
          </div>
          <img src={authArtwork} alt="Миша с картой готовится к путешествию по России" />
        </aside>
      </div>
    </main>
  )
}
