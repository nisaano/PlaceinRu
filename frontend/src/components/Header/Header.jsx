import { UserIcon } from '../UserIcon/UserIcon'
import './Header.css'

/** Единая фиксированная навигация с оригинальной составной иконкой пользователя. */
export function Header() {
  return (
    <header className="header">
      <a className="brand" href="#top">
        <strong>PR</strong>
        <span>PlaceinRu</span>
      </a>
      <nav aria-label="Основная навигация">
        <a href="#top">Главное</a>
        <a href="#about">Сообщество</a>
        <a href="#mission">О проекте</a>
      </nav>
      <a className="login" href="#assistant">
        <UserIcon /> вход
      </a>
    </header>
  )
}
