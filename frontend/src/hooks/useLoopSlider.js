import { useCallback, useState } from 'react'

/**
 * Управляет циклической лентой с клонами крайних элементов.
 * После перехода на технический клон позиция возвращается к оригиналу без анимации.
 */
export function useLoopSlider(itemCount) {
  const [position, setPosition] = useState(1)
  const [animated, setAnimated] = useState(true)
  const [moving, setMoving] = useState(false)

  const move = useCallback(
    (direction) => {
      if (moving) return
      setAnimated(true)
      setMoving(true)
      setPosition((value) => value + direction)
    },
    [moving],
  )

  const settle = useCallback(
    (event) => {
      // Игнорируем всплывшие transitionend от возможных дочерних элементов карточки.
      if (event && event.target !== event.currentTarget) return

      setMoving(false)
      if (position === 0) {
        setAnimated(false)
        setPosition(itemCount)
      } else if (position === itemCount + 1) {
        setAnimated(false)
        setPosition(1)
      }
    },
    [itemCount, position],
  )

  return { position, animated, moving, move, settle }
}
