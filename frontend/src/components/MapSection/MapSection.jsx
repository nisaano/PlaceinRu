import mapBackground from '../../assets/figma/about-map.png'
import { InteractiveRussiaMap } from '../InteractiveRussiaMap/InteractiveRussiaMap'
import './MapSection.css'

/** Обрамление интерактивной карты: заголовок, лесной фон и географический компонент. */
export function MapSection() {
  return (
    <section
      className="map-section"
      id="map"
      style={{ '--map-background': `url(${mapBackground})` }}
    >
      <div className="map-section__content">
        <div className="map-section__copy">
          <h2>Карта России</h2>
          <p>
            Кликните на регион,
            <br />
            чтобы узнать больше о местах,
            <br />
            маршрутах и путешествиях
          </p>
        </div>
        <InteractiveRussiaMap />
      </div>
    </section>
  )
}
