import headOuter from '../../assets/figma/login-head.svg'
import headInner from '../../assets/figma/login-face.svg'
import bodyOuter from '../../assets/figma/login-head-outer.svg'
import bodyInner from '../../assets/figma/login-shoulders.svg'
import './UserIcon.css'

/** Собирает оригинальную иконку входа из четырёх экспортированных слоёв Figma. */
export function UserIcon({ className = '' }) {
  return (
    <span className={`user-icon ${className}`.trim()} aria-hidden="true">
      <img className="user-icon__head" src={headOuter} alt="" />
      <img className="user-icon__face" src={headInner} alt="" />
      <img className="user-icon__body" src={bodyOuter} alt="" />
      <img className="user-icon__body-inner" src={bodyInner} alt="" />
    </span>
  )
}
