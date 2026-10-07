import { Icon } from './Icon'

export function ErrorNotice({ message, onRetry }) {
  return (
    <div className="notice notice--error" role="alert">
      <Icon name="alert" size={22} />
      <div>
        <strong>Не получилось загрузить данные</strong>
        <p>{message}</p>
      </div>
      {onRetry && (
        <button className="button button--small button--outline" onClick={onRetry}>
          Повторить
        </button>
      )}
    </div>
  )
}

export function EmptyNotice({ title, children, action }) {
  return (
    <div className="empty-notice">
      <span className="empty-notice__icon">
        <Icon name="sun" size={26} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  )
}

export function LoadingState({ children = 'Загружаем данные…' }) {
  return (
    <div className="loading-state">
      <span className="spinner" />
      {children}
    </div>
  )
}
