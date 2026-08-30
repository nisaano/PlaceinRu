import wave from '../../assets/mission-reviews-wave.png'
import paper from '../../assets/reviews-paper.png'
import { MissionSection } from '../MissionSection/MissionSection'
import { PlacesSection } from '../PlacesSection/PlacesSection'
import './MissionReviewsFlow.css'

/**
 * Общая сцена миссии и отзывов.
 * Два бумажных слоя намеренно пересекают границу дочерних секций.
 */
export function MissionReviewsFlow() {
  return (
    <div className="mission-reviews-flow">
      <div className="mission-reviews-flow__stage">
        <div className="mission-reviews-flow__art" aria-hidden="true">
          <img className="mission-reviews-flow__wave" src={wave} alt="" />
          <img className="mission-reviews-flow__paper" src={paper} alt="" />
        </div>
        <MissionSection />
        <PlacesSection />
      </div>
    </div>
  )
}
