import { useEffect, useState } from 'react'
import { Hero } from '../../components/Hero/Hero'
import { MapSection } from '../../components/MapSection/MapSection'
import { QuizSection } from '../../components/QuizSection/QuizSection'
import { StorySection } from '../../components/StorySection/StorySection'
import { MissionReviewsFlow } from '../../components/MissionReviewsFlow/MissionReviewsFlow'
import { CtaSection } from '../../components/CtaSection/CtaSection'
import { Footer } from '../../components/Footer/Footer'

/** Собирает секции лендинга и передаёт им общий коэффициент широкоформатной сцены. */
export function HomePage() {
  const [wideScale, setWideScale] = useState(() =>
    typeof window === 'undefined' ? 1 : Math.max(1, document.documentElement.clientWidth / 1280),
  )

  useEffect(() => {
    let frameId
    const updateScale = () => {
      window.cancelAnimationFrame(frameId)
      frameId = window.requestAnimationFrame(() => {
        setWideScale(Math.max(1, document.documentElement.clientWidth / 1280))
      })
    }

    updateScale()
    window.addEventListener('resize', updateScale)
    return () => {
      window.cancelAnimationFrame(frameId)
      window.removeEventListener('resize', updateScale)
    }
  }, [])

  // Секции после карты построены на сцене 1280 px и масштабируются как единая композиция.
  const responsiveSizes = {
    '--wide-scale': wideScale,
    '--scaled-650': `${650 * wideScale}px`,
    '--scaled-800': `${800 * wideScale}px`,
    '--scaled-1380': `${1380 * wideScale}px`,
  }

  return (
    <>
      <Hero />
      <main style={responsiveSizes}>
        <MapSection />
        <QuizSection />
        <StorySection />
        <MissionReviewsFlow />
        <CtaSection />
      </main>
      <Footer />
    </>
  )
}
