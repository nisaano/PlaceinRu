import { useState } from 'react'
import background from '../../assets/figma/assistant-background.png'
import moscow from '../../assets/figma/assistant-moscow.png'
import region from '../../assets/figma/assistant-region.png'
import { useLoopSlider } from '../../hooks/useLoopSlider'
import './QuizSection.css'

const places = [
  {
    image: moscow,
    title: 'Москва',
    text: 'Столица России: Кремль, Красная площадь, лучшие музеи и бесконечные возможности для досуга.',
  },
  {
    image: region,
    title: 'Московская область',
    text: 'Древние города, усадьбы, живописные леса и реки. Идеально для выезда на природу.',
  },
]
const loopPlaces = [places.at(-1), ...places, ...places]

/** Экран поиска направления и компактный слайдер рекомендуемых мест. */
export function QuizSection() {
  const [query, setQuery] = useState('')
  const { position, animated, moving, move, settle } = useLoopSlider(places.length)

  return (
    <section className="assistant" id="assistant">
      <div className="assistant__stage">
        <div className="assistant__panel" style={{ '--assistant': `url(${background})` }}>
          <h2>Куда хотите поехать?</h2>
          <p className="assistant__subtitle">Миша подберёт идеальные места и подходящие маршруты</p>
          <form className="assistant__search" onSubmit={(event) => event.preventDefault()}>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Напишите ваш запрос..."
            />
            <label className="date-picker" title="Выбрать дату">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M7 2v3M17 2v3M3 9h18M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2Z" />
              </svg>
              <span className="sr-only">Дата поездки</span>
              <input type="date" aria-label="Дата поездки" />
            </label>
            <button type="submit">Подобрать</button>
          </form>
          <div className="assistant__cards">
            <button
              type="button"
              className="card-arrow"
              disabled={moving}
              onClick={() => move(-1)}
              aria-label="Предыдущие места"
            >
              ←
            </button>
            <div className="assistant__viewport">
              <div
                className={`assistant__track${animated ? ' is-animated' : ''}`}
                style={{ '--position': position }}
                onTransitionEnd={settle}
              >
                {loopPlaces.map((place, index) => (
                  <PlaceCard key={`${place.title}-${index}`} {...place} />
                ))}
              </div>
            </div>
            <button
              type="button"
              className="card-arrow"
              disabled={moving}
              onClick={() => move(1)}
              aria-label="Следующие места"
            >
              →
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

function PlaceCard({ image, title, text }) {
  return (
    <article className="assistant-card">
      <img src={image} alt={title} />
      <h3>{title}</h3>
      <p>{text}</p>
      <a href="#map">Подробнее</a>
    </article>
  )
}
