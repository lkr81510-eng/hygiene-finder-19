import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const KOREA_VIEW = { center: [36.35, 127.85], zoom: 7 }

function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

/**
 * Leaflet + OpenStreetMap 지도 (API 키 불필요).
 * - 지도 클릭 → onPick({lat, lng})
 * - 업소 마커 클릭 → onSelect(id), selectedId 가 바뀌면 해당 마커 강조
 */
export default function NearbyMap({ center, radius, items, selectedId, onPick, onSelect }) {
  const elRef = useRef(null)
  const mapRef = useRef(null)
  const layersRef = useRef({ area: null, shops: null, markers: new Map() })
  const handlers = useRef({ onPick, onSelect })
  handlers.current = { onPick, onSelect }

  // 지도 생성 (한 번)
  useEffect(() => {
    const map = L.map(elRef.current, { zoomControl: true, attributionControl: true }).setView(
      KOREA_VIEW.center,
      KOREA_VIEW.zoom,
    )
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map)
    map.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>')
    map.on('click', (e) => handlers.current.onPick?.({ lat: e.latlng.lat, lng: e.latlng.lng }))
    layersRef.current.area = L.layerGroup().addTo(map)
    layersRef.current.shops = L.layerGroup().addTo(map)
    mapRef.current = map

    // 레이아웃이 잡힌 뒤 크기 재계산 (그리드/반응형 대응)
    const ro = new ResizeObserver(() => map.invalidateSize())
    ro.observe(elRef.current)
    return () => {
      ro.disconnect()
      map.remove()
      mapRef.current = null
    }
  }, [])

  // 검색 중심 + 반경 원
  useEffect(() => {
    const map = mapRef.current
    const { area } = layersRef.current
    if (!map) return
    area.clearLayers()
    if (!center) return
    const accent = cssVar('--accent', '#2a78d6')
    const circle = L.circle([center.lat, center.lng], {
      radius,
      color: accent,
      weight: 1.5,
      fillColor: accent,
      fillOpacity: 0.06,
      interactive: false,
    }).addTo(area)
    L.circleMarker([center.lat, center.lng], {
      radius: 7,
      color: '#ffffff',
      weight: 3,
      fillColor: '#0b0b0b',
      fillOpacity: 1,
      interactive: false,
    })
      .bindTooltip(center.label || '검색 위치', { direction: 'top', offset: [0, -8] })
      .addTo(area)
    map.fitBounds(circle.getBounds(), { padding: [24, 24] })
  }, [center, radius])

  // 업소 마커
  useEffect(() => {
    const { shops, markers } = layersRef.current
    if (!shops) return
    shops.clearLayers()
    markers.clear()
    const fill = cssVar('--series', '#2a78d6')
    for (const s of items) {
      const m = L.circleMarker([s.lat, s.lng], {
        radius: 6,
        color: '#ffffff',
        weight: 2,
        fillColor: fill,
        fillOpacity: 0.9,
      })
        .bindTooltip(`${s.bssh_nm} · ${s.distance_m < 1000 ? `${s.distance_m}m` : `${(s.distance_m / 1000).toFixed(1)}km`}`, {
          direction: 'top',
          offset: [0, -6],
        })
        .on('click', (e) => {
          L.DomEvent.stopPropagation(e) // 지도 클릭(위치 변경)으로 번지지 않게
          handlers.current.onSelect?.(s.id)
        })
        .addTo(shops)
      markers.set(s.id, m)
    }
  }, [items])

  // 선택된 업소 강조
  useEffect(() => {
    const map = mapRef.current
    const { markers } = layersRef.current
    if (!map) return
    const fill = cssVar('--series', '#2a78d6')
    const hi = cssVar('--highlight', '#eb6834')
    markers.forEach((m, id) => {
      const on = id === selectedId
      m.setStyle({ radius: on ? 11 : 6, fillColor: on ? hi : fill, weight: on ? 3 : 2 })
      if (on) {
        m.bringToFront()
        m.openTooltip()
        if (!map.getBounds().contains(m.getLatLng())) map.panTo(m.getLatLng())
      } else {
        m.closeTooltip()
      }
    })
  }, [selectedId, items])

  return <div ref={elRef} className="map" role="application" aria-label="주변 업소 지도. 지도를 클릭하면 그 위치로 검색합니다." />
}
