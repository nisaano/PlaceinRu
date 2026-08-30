import { useCallback, useEffect, useMemo, useState } from 'react'
import { geoConicEqualArea, geoPath } from 'd3-geo'
import { feature } from 'topojson-client'
import topo from '../../assets/data/russia-regions.json'
import './InteractiveRussiaMap.css'

const districtColors = {
  ЦФО: '#8fbd72',
  СЗФО: '#79ad69',
  ЮФО: '#a6ca82',
  СКФО: '#91bc70',
  ПФО: '#76ad66',
  УФО: '#9ac77b',
  СФО: '#84b66c',
  ДФО: '#a1c77d',
}

/** Строит кликабельные SVG-пути субъектов из локального TopoJSON. */
export function InteractiveRussiaMap() {
  // Геометрию 89 регионов вычисляем один раз: повторная проекция на каждом рендере дорогая.
  const { regions, paths } = useMemo(() => {
    const regions = feature(topo, topo.objects.ru89).features
    const projection = geoConicEqualArea()
      .parallels([50, 70])
      .rotate([-100, 0])
      .fitExtent(
        [
          [20, 24],
          [980, 510],
        ],
        { type: 'FeatureCollection', features: regions },
      )
    const makePath = geoPath(projection)
    return {
      regions,
      paths: new Map(regions.map((region) => [region.properties.id, makePath(region)])),
    }
  }, [])
  const [selected, setSelected] = useState(null)
  const [hovered, setHovered] = useState(null)

  const clearSelection = useCallback(() => {
    setSelected(null)
    if (window.location.hash.startsWith('#region-')) {
      window.history.replaceState(null, '', '#map')
    }
  }, [])

  useEffect(() => {
    if (!selected) return undefined
    const timer = window.setTimeout(clearSelection, 6500)
    return () => window.clearTimeout(timer)
  }, [clearSelection, selected])

  const select = (region) => {
    setSelected(region)
    window.history.replaceState(null, '', `#region-${region.properties.id}`)
  }

  return (
    <div className="russia-map">
      <svg viewBox="0 0 1000 540" role="group" aria-label="Интерактивная карта 89 регионов России">
        <g className="russia-map__regions">
          {regions.map((region) => (
            <path
              key={region.properties.id}
              d={paths.get(region.properties.id)}
              style={{ '--region-color': districtColors[region.properties.fd] || '#91bd72' }}
              className={selected?.properties.id === region.properties.id ? 'is-active' : ''}
              role="button"
              tabIndex="0"
              aria-label={region.properties.name_full}
              onMouseEnter={() => setHovered(region)}
              onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(region)}
              onBlur={() => setHovered(null)}
              onClick={() => select(region)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  select(region)
                }
              }}
            />
          ))}
        </g>
      </svg>
      {hovered && (
        <div className="region-tooltip" role="tooltip">
          <b>{hovered.properties.name}</b>
          <span>{hovered.properties.capital}</span>
        </div>
      )}
      {selected && (
        <article
          className="region-placeholder"
          id={`region-${selected.properties.id}`}
          aria-live="polite"
        >
          <button
            className="region-placeholder__close"
            type="button"
            onClick={clearSelection}
            aria-label="Закрыть информацию о регионе"
          >
            ×
          </button>
          <span>Выбран регион</span>
          <strong>{selected.properties.name_full}</strong>
          <p>
            Центр: {selected.properties.capital}. Страница региона и готовые маршруты появятся в
            следующем обновлении.
          </p>
          <em>Скоро</em>
        </article>
      )}
    </div>
  )
}
