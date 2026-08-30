import landscape from '../../assets/figma/mission-landscape.png'
import illustration from '../../assets/figma/mission-illustration.png'
import icon1 from '../../assets/figma/mission-icon-01.png'
import icon2 from '../../assets/figma/mission-icon-02.png'
import icon3 from '../../assets/figma/mission-icon-03.png'
import icon4 from '../../assets/figma/mission-icon-04.png'
import './MissionSection.css'

const items = [
  [icon1, 'провереные места и отзывы'],
  [icon2, 'большая база достопримечательностей'],
  [icon3, 'удобное планирование маршрутов'],
  [icon4, 'полезные советы перед поездкой'],
]

/** Секция миссии и четырёх принципов продукта. */
export function MissionSection() {
  return (
    <section className="mission" id="mission">
      <div className="mission__stage">
        <div className="mission__brand">
          <b>PR</b>
          <span>PlaceinRu</span>
        </div>
        <div className="mission__intro">
          <h2>Наша цель</h2>
          <p>
            Создавать новые возможности для путешествий по России и делать их интересными, удобными
            и доступными для всех.
          </p>
        </div>
        <div className="mission__items">
          {items.map(([icon, label]) => (
            <article key={label}>
              <img src={icon} alt="" />
              <span>{label}</span>
            </article>
          ))}
        </div>
        <img className="mission__route" src={landscape} alt="" />
        <img className="mission__trees" src={illustration} alt="" />
      </div>
    </section>
  )
}
