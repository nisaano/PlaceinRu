import forest from '../../assets/figma/about-01.png'
import lighthouse from '../../assets/figma/about-02.png'
import canyon from '../../assets/figma/about-03.png'
import geyser from '../../assets/figma/about-04.png'
import image5 from '../../assets/figma/about-05.png'
import image6 from '../../assets/figma/about-06.png'
import snowboarder from '../../assets/figma/about-07.png'
import mountains from '../../assets/figma/about-08.png'
import centerBackground from '../../assets/figma/about-main.png'
import routeDecoration from '../../assets/figma/about-strip.png'
import regions from '../../assets/figma/stat-regions.png'
import routes from '../../assets/figma/stat-routes.png'
import places from '../../assets/figma/stat-places.png'
import users from '../../assets/figma/stat-users.png'
import statsPanel from '../../assets/figma/about-stats-panel.svg'
import vk from '../../assets/figma/vk.svg'
import telegram from '../../assets/figma/telegram.svg'
import max from '../../assets/figma/max.svg'
import './StorySection.css'

/** Коллаж о проекте, социальные ссылки и краткая статистика платформы. */
export function StorySection() {
  return (
    <section className="about" id="about">
      <div className="about__stage">
        <div className="about__gallery">
          <img className="about__image about__image--1" src={lighthouse} alt="Маяк на берегу" />
          <img className="about__image about__image--2" src={centerBackground} alt="Горный лес" />
          <img
            className="about__image about__image--3"
            src={canyon}
            alt="Дорога вдоль горной реки"
          />
          <img className="about__image about__image--4" src={forest} alt="Лесная тропа" />
          <img className="about__image about__image--5" src={image5} alt="Миша у водопада" />
          <img className="about__image about__image--6" src={geyser} alt="Долина гейзеров" />
          <img
            className="about__image about__image--7"
            src={image6}
            alt="Миша фотографирует маяк"
          />
        </div>
        <div className="about__polaroid">
          <img src={snowboarder} alt="Миша в горах" />
          <span>PR</span>
        </div>
        <img className="about__mountains" src={mountains} alt="" />
        <img className="about__route" src={routeDecoration} alt="" />
        <h2>Place in RU</h2>
        <div className="about__social">
          <span>больше о нас</span>
          <a href="https://vk.com" aria-label="ВКонтакте">
            <img src={vk} alt="" />
          </a>
          <a href="https://t.me" aria-label="Telegram">
            <img src={telegram} alt="" />
          </a>
          <a href="https://max.ru" aria-label="Max">
            <img src={max} alt="" />
          </a>
        </div>
        <p className="about__lead">
          Платформа для тех, кто любит путешествовать, выбирать направления и открывать Россию
          по-новому.
        </p>
        <div className="about__promise-group">
          <h3>Мы собираем лучшее</h3>
          <p className="about__promise">делая ваши путешествия лёгкими, яркими и запоминающимися</p>
        </div>
        <div className="about__stats">
          <img className="about__stats-bg" src={statsPanel} alt="" />
          <Stat image={regions} number="89" label="Регионов России" />
          <Stat image={places} number="1200+" label="Достопримечательностей" />
          <Stat image={users} number="7" label="Пользователей" />
          <Stat image={routes} number="89" label="Готовых маршрутов" />
        </div>
      </div>
    </section>
  )
}

function Stat({ image, number, label }) {
  return (
    <div className="about-stat">
      <img src={image} alt="" />
      <span>
        <b>{number}</b>
        <small>{label}</small>
      </span>
    </div>
  )
}
