import { useState } from 'react'
import image1 from '../../assets/figma/community-01.png'
import image2 from '../../assets/figma/community-02.png'
import image3 from '../../assets/figma/community-03.png'
import avatar1 from '../../assets/figma/avatar-01.png'
import avatar2 from '../../assets/figma/avatar-02.png'
import avatar3 from '../../assets/figma/avatar-03.png'
import save from '../../assets/figma/save.svg'
import like from '../../assets/figma/like.svg'
import arrow from '../../assets/reviews-arrow-right.svg'
import { useLoopSlider } from '../../hooks/useLoopSlider'
import './PlacesSection.css'

const posts = [
  { id: 1, image: image1, avatar: avatar1, name: 'Александр Великий', tag: '#камчатка #горы' },
  { id: 2, image: image2, avatar: avatar2, name: 'Анна Быстрова', tag: '...' },
  { id: 3, image: image3, avatar: avatar3, name: 'Дмитрий_18', tag: '...' },
]
const loopPosts = [posts.at(-1), ...posts, ...posts]

/** Галерея публикаций сообщества; вся белая карточка перемещается внутри ленты. */
export function PlacesSection() {
  const [liked, setLiked] = useState([])
  const { position, animated, moving, move, settle } = useLoopSlider(posts.length)
  const toggle = (id) =>
    setLiked((value) => (value.includes(id) ? value.filter((item) => item !== id) : [...value, id]))
  return (
    <section className="community" id="community">
      <div className="community__stage">
        <h2>PlaceinRu</h2>
        <button
          type="button"
          className="community__arrow community__arrow--left"
          disabled={moving}
          onClick={() => move(-1)}
          aria-label="Предыдущие публикации"
        >
          <img src={arrow} alt="" />
        </button>
        <div className="community__viewport">
          <div
            className={`community__track${animated ? ' is-animated' : ''}`}
            style={{ '--position': position }}
            onTransitionEnd={settle}
          >
            {loopPosts.map((post, index) => (
              <PostCard
                key={`${post.id}-${index}`}
                post={post}
                liked={liked.includes(post.id)}
                onLike={() => toggle(post.id)}
              />
            ))}
          </div>
        </div>
        <button
          type="button"
          className="community__arrow community__arrow--right"
          disabled={moving}
          onClick={() => move(1)}
          aria-label="Следующие публикации"
        >
          <img src={arrow} alt="" />
        </button>
        <a className="community__share" href="#assistant">
          поделиться путешествием
        </a>
      </div>
    </section>
  )
}

function PostCard({ post, liked, onLike }) {
  return (
    <article className="community-card">
      <img className="community-card__photo" src={post.image} alt="Путешествие по России" />
      <div className="community-card__author">
        <img src={post.avatar} alt="" />
        <b>{post.name}</b>
      </div>
      <p>{post.tag}</p>
      <span className="community-card__line" aria-hidden="true" />
      <div className="community-card__actions">
        <button type="button" aria-label="Сохранить">
          <img src={save} alt="" />
        </button>
        <button
          type="button"
          className={liked ? 'is-liked' : ''}
          onClick={onLike}
          aria-label="Нравится"
        >
          <img src={like} alt="" />
        </button>
        <span>{6 + (liked ? 1 : 0)}</span>
      </div>
    </article>
  )
}
