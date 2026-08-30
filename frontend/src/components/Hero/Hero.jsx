import hero from '../../assets/figma/hero-background.png'
import { Header } from '../Header/Header'
import './Hero.css'

/** Первый экран: позиционирует основное сообщение поверх оригинального фона Figma. */
export function Hero() {
  return (
    <section className="hero" id="top" style={{ '--hero': `url(${hero})` }}>
      <Header />
      <div className="hero__shade" aria-hidden="true" />
      <div className="hero__content">
        <p>Ваши путешествия начинаются здесь</p>
        <h1>
          Открой <span>Россию</span>
          <br />
          по-новому
        </h1>
        <a href="#map">
          Построить маршрут <b>→</b>
        </a>
      </div>
      <a className="hero__arrow" href="#map" aria-label="Перейти к карте">
        ⌄
      </a>
    </section>
  )
}
