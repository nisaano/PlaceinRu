import mascotLandscape from '../../assets/figma/hero-background.png'
import mishaForest from '../../assets/figma/assistant-background.png'
import destinationKamchatka from '../../assets/figma/about-main.png'
import destinationAltai from '../../assets/figma/about-03.png'
import destinationBaikal from '../../assets/figma/community-03.png'
import destinationKarelia from '../../assets/figma/about-01.png'
import destinationGoldenRing from '../../assets/figma/community-02.png'
import { Icon } from '../../components/common/Icon'
import { Link } from '../../router/Router'
import { useAuth } from '../../auth/AuthContext'
import { useState } from 'react'
import './LandingPage.css'

const benefits = [
  ['sparkle', 'Умные рекомендации'],
  ['suitcase', 'Билеты и отели'],
  ['map', 'Готовый маршрут'],
  ['support', 'Поддержка 24/7'],
  ['settings', 'Гибкие настройки'],
  ['shield', 'Вся Россия в одном месте'],
]
const steps = [
  ['Расскажите, куда хотите', 'Выберите направление или просто напишите Мише, что вам интересно.'],
  ['Получите предложения', 'AI подберёт подходящие места, отели и варианты маршрута.'],
  ['Выберите и настройте', 'Добавляйте, убирайте и меняйте места под себя — в один клик.'],
  ['Путешествуйте легко', 'Сохраните маршрут с расписанием, картой и деталями поездки.'],
]
const destinations = [
  ['Камчатка', 'Вулканы, океан, дикая природа', destinationKamchatka],
  ['Алтай', 'Горы, реки, чистый воздух', destinationAltai],
  ['Байкал', 'Уникальная природа и энергия', destinationBaikal],
  ['Карелия', 'Тишина, леса, озёра', destinationKarelia],
  ['Золотое кольцо', 'История и культура', destinationGoldenRing],
]
const features = [
  ['suitcase', 'Всё в одном месте', 'От идеи до бронирования — без лишних вкладок и сайтов.'],
  [
    'sparkle',
    'Удобный AI-помощник',
    'Миша всегда рядом, чтобы помочь, подсказать и изменить маршрут.',
  ],
  ['settings', 'Гибкость', 'Меняйте план в любой момент, даже во время поездки.'],
  ['support', 'Поддержка 24/7', 'Миша рядом, когда вам это нужно.'],
]

export function LandingPage() {
  const { user } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const startPath = user ? '/app/misha' : '/register'
  return (
    <main className="landing-shell">
      <div className="landing-page">
        <header className="landing-header">
          <Link className="landing-brand" to="/">
            <span className="brand-pin">
              <Icon name="pin" size={20} />
            </span>
            <b>PlaceinRu</b>
          </Link>
          <nav
            className={`landing-nav ${menuOpen ? 'is-open' : ''}`}
            aria-label="Главная навигация"
          >
            <a href="#about" onClick={() => setMenuOpen(false)}>
              О проекте
            </a>
            <a href="#features" onClick={() => setMenuOpen(false)}>
              Возможности
            </a>
            <a href="#destinations" onClick={() => setMenuOpen(false)}>
              Маршруты
            </a>
            <a href="#reviews" onClick={() => setMenuOpen(false)}>
              Отзывы
            </a>
            <a href="#faq" onClick={() => setMenuOpen(false)}>
              FAQ
            </a>
          </nav>
          <div className="landing-header__actions">
            <Link className="button button--primary button--header" to={user ? '/app' : '/login'}>
              {user ? 'Кабинет' : 'Войти'}
            </Link>
          </div>
        </header>

        <section className="landing-hero" style={{ '--hero-image': `url(${mascotLandscape})` }}>
          <div className="landing-hero__copy">
            <span className="eyebrow">
              <Icon name="sun" size={16} /> Путешествуй по России
            </span>
            <h1>Твой идеальный маршрут по России — в чате</h1>
            <p>
              Планируй поездки с AI-помощником. Открывай новые места и собирай путешествие, которое
              подходит именно тебе.
            </p>
            <div className="landing-hero__buttons">
              <Link className="button button--primary" to={startPath}>
                Попробовать Мишу <Icon name="arrow" size={19} />
              </Link>
              <a className="button button--soft" href="#how-it-works">
                Узнать больше
              </a>
            </div>
            <span className="scribble">
              Путешествуй
              <br />
              по России!
            </span>
          </div>
        </section>

        <div className="benefit-strip" aria-label="Возможности PlaceinRu">
          {benefits.map(([icon, label]) => (
            <div className="benefit-strip__item" key={label}>
              <span>
                <Icon name={icon} size={21} />
              </span>
              <b>{label}</b>
            </div>
          ))}
        </div>

        <section className="landing-section how-section" id="how-it-works">
          <div className="section-heading">
            <span className="section-doodle">
              <Icon name="mountain" size={24} />
            </span>
            <div>
              <h2>Как это работает?</h2>
              <p>Всего несколько шагов — и путешествие почти готово</p>
            </div>
            <span className="sun-doodle">
              <Icon name="sun" size={22} />
            </span>
          </div>
          <div className="steps-grid">
            {steps.map(([title, text], index) => (
              <article className="step-card" key={title}>
                <span className="step-number">{index + 1}</span>
                <div>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
                <Icon name={['chat', 'pin', 'edit', 'file'][index]} size={24} />
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section destinations-section" id="destinations">
          <div className="section-heading">
            <span className="section-doodle">
              <Icon name="mountain" size={24} />
            </span>
            <div>
              <h2>Популярные направления</h2>
              <p>Вдохновляйся лучшими маршрутами по России</p>
            </div>
            <span className="sun-doodle">
              <Icon name="sun" size={22} />
            </span>
          </div>
          <div className="destination-grid">
            {destinations.map(([name, note, image]) => (
              <Link className="destination-card" to={startPath} key={name}>
                <img src={image} alt={`Пейзаж направления ${name}`} />
                <div>
                  <div>
                    <h3>{name}</h3>
                    <p>{note}</p>
                  </div>
                  <span className="round-arrow">
                    <Icon name="arrow" size={15} />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section className="landing-section feature-section" id="features">
          <div className="feature-copy">
            <div className="section-heading">
              <span className="section-doodle">
                <Icon name="heart" size={24} />
              </span>
              <h2>Почему PlaceinRu?</h2>
            </div>
            <div className="feature-list">
              {features.map(([icon, title, text]) => (
                <article key={title}>
                  <span>
                    <Icon name={icon} size={21} />
                  </span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </article>
              ))}
            </div>
          </div>
          <div className="misha-preview" style={{ backgroundImage: `url(${mishaForest})` }}>
            <div className="chat-bubble">
              Привет! Куда хочешь отправиться? Я помогу тебе спланировать идеальное путешествие по
              России.
            </div>
          </div>
        </section>

        <section className="landing-cta" id="about">
          <div className="landing-cta__copy">
            <span className="eyebrow">Всё начинается с мечты</span>
            <h2>
              Готовы отправиться
              <br />в путешествие?
            </h2>
            <p>Соберите своё идеальное путешествие уже сегодня.</p>
            <Link className="button button--primary" to={startPath}>
              Попробовать Мишу <Icon name="arrow" size={18} />
            </Link>
          </div>
        </section>

        <section className="landing-reviews" id="reviews">
          <span className="eyebrow">Истории путешественников</span>
          <h2>Каждая поездка — своя история</h2>
          <p>Когда появятся отзывы путешественников, мы соберём их здесь.</p>
        </section>
        <section className="landing-faq" id="faq">
          <h2>Частые вопросы</h2>
          <details>
            <summary>Что умеет Миша?</summary>
            <p>
              Миша помогает уточнить параметры поездки и подобрать направления по текущему каталогу
              сервиса.
            </p>
          </details>
          <details>
            <summary>Можно ли изменить поездку позже?</summary>
            <p>
              Сохранённые путешествия доступны в личном кабинете. Поддерживаемые изменения зависят
              от подключённых операций Backend и MRT.
            </p>
          </details>
        </section>
        <footer className="landing-footer">
          <Link className="landing-brand" to="/">
            <span className="brand-pin">
              <Icon name="pin" size={18} />
            </span>
            <b>PlaceinRu</b>
          </Link>
          <span>Твой маршрут по России</span>
          <nav>
            <a href="#about">О проекте</a>
            <a href="#features">Возможности</a>
            <a href="#faq">FAQ</a>
          </nav>
          <small>© 2026 PlaceinRu</small>
        </footer>
      </div>
    </main>
  )
}
