import bus from '../../assets/figma/bus.png'
import calendarIcon from '../../assets/figma/mission-icon-04.png'
import routeIcon from '../../assets/figma/mission-icon-03.png'
import reviewsIcon from '../../assets/figma/mission-icon-01.png'
import placesIcon from '../../assets/figma/mission-icon-02.png'
import './MissionSection.css'

const advantages = [
  [calendarIcon, 'удобное планирование маршрутов'],
  [routeIcon, 'полезные советы перед поездкой'],
  [reviewsIcon, 'проверенные места и отзывы'],
  [placesIcon, 'большая база достопримечательностей'],
]

/** Обновлённый экран о проекте с автобусом и четырьмя преимуществами сервиса. */
export function MissionSection() {
  return (
    <section className="mission" id="mission">
      <div className="mission__stage">
        <h2 className="mission__title">
          Делаем путешествия
          <br />
          по России проще и
          <br />
          интереснее
        </h2>

        <p className="mission__description">
          Сервис, который помогает находить интересные места,
          <br />
          создавать маршруты и путешествовать с удовольствием.
        </p>

        <img className="mission__bus" src={bus} alt="Туристический автобус" />

        <div className="mission__advantages">
          {advantages.map(([icon, label]) => (
            <article className="mission-advantage" key={label}>
              <img src={icon} alt="" />
              <span>{label}</span>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
