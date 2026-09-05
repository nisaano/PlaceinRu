import image from '../../assets/figma/guide-cta.png'
import './CtaSection.css'

/** Финальный призыв для гидов перед подвалом. */
export function CtaSection() {
  return (
    <section className="guide">
      <div className="guide__stage">
        <div className="guide__card" style={{ '--guide': `url(${image})` }}>
          <div>
            <h2>Есть места, о которых хочется рассказать...</h2>
            <p>Проводите людей по любимым местам, открывайте им знакомую Россию с новой стороны.</p>
            <div className="guide__action">
              <a href="#assistant">Разместить тур</a>
              <span>Для гидов</span>
            </div>
          </div>
          <b>PR</b>
          <strong>PlaceinRu</strong>
        </div>
      </div>
    </section>
  )
}
