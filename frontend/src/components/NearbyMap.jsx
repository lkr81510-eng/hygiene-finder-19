import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const KOREA_VIEW = { center: [36.35, 127.85], zoom: 7 }
const FIT_OPTIONS = { padding: [28, 28], maxZoom: 17 }

function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

/**
 * Leaflet + OpenStreetMap 지도 (API 키 불필요).
 * - 지도 클릭 → onPick({lat, lng})
 * - 업소 마커 클릭 → onSelect(id), selectedId 가 바뀌면 해당 마커 강조
 * - 결과가 바뀔 때마다 반경 원과 모든 마커가 보이도록 범위를 자동으로 맞춘다
 */
export default function NearbyMap({ center, radius, items, selectedId, onPick, onSelect }) {
  const elRef = useRef(null)
  const mapRef = useRef(null)
  const layersRef = useRef({ area: null, shops: null, markers: new Map(), circle: null })
  const areaRef = useRef(null) // { lat, lng, radius } — 범위 계산용
  const handlers = useRef({ onPick, onSelect })
  handlers.current = { onPick, onSelect }

  // 반경 원 + 모든 마커를 포함하는 범위.
  // circle.getBounds() 는 화면 픽셀 좌표로 계산해서 확대·축소 애니메이션 중에는 틀린 값을 줄 수 있으므로
  // 중심 좌표와 반경(m)으로 지리적으로 계산한다.
  function targetBounds() {
    const a = areaRef.current
    if (!a) return null
    const b = L.latLng(a.lat, a.lng).toBounds(a.radius * 2)
    layersRef.current.markers.forEach((m) => b.extend(m.getLatLng()))
    return b
  }

  function fitAll() {
    const map = mapRef.current
    const b = targetBounds()
    if (!map || !b) return
    map.invalidateSize({ pan: false })
    map.fitBounds(b, FIT_OPTIONS)
  }

  // 현재 화면이 반경 원을 다 담지 못하거나, 필요 이상으로 축소돼 있으면 true
  function needsRefit() {
    const map = mapRef.current
    const b = targetBounds()
    if (!map || !b) return false
    const fitZoom = map.getBoundsZoom(b, false, L.point(FIT_OPTIONS.padding))
    return !map.getBounds().contains(b) || map.getZoom() < Math.min(fitZoom, FIT_OPTIONS.maxZoom) - 1
  }

  // 지도 생성 (한 번)
  useEffect(() => {
    const map = L.map(elRef.current, {
      zoomControl: true,
      attributionControl: true,
      // 페이지를 스크롤하다 지도가 확대·축소되지 않게, 휠 확대·축소는 Ctrl(⌘)+휠 일 때만 (아래 wheel 처리)
      scrollWheelZoom: false,
    }).setView(KOREA_VIEW.center, KOREA_VIEW.zoom)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map)
    map.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>')

    map.on('click', (e) => handlers.current.onPick?.({ lat: e.latlng.lat, lng: e.latlng.lng }))

    // Ctrl(⌘)+휠: 지도 확대·축소 / 그냥 휠: 페이지 스크롤 + 안내 표시
    const container = map.getContainer()
    const hint = L.DomUtil.create('div', 'map-wheel-hint', container)
    hint.textContent = 'Ctrl(⌘) + 스크롤로 지도를 확대·축소할 수 있어요'
    let hintTimer = null
    let wheelLock = 0
    const onWheel = (e) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault()
        const now = Date.now()
        if (now - wheelLock < 180) return // 트랙패드 연속 이벤트 완화
        wheelLock = now
        const delta = e.deltaY < 0 ? 1 : -1
        map.setZoomAround(map.mouseEventToContainerPoint(e), map.getZoom() + delta)
      } else {
        hint.classList.add('show')
        clearTimeout(hintTimer)
        hintTimer = setTimeout(() => hint.classList.remove('show'), 1200)
      }
    }
    container.addEventListener('wheel', onWheel, { passive: false })

    // "반경 전체 보기" 버튼
    const FitControl = L.Control.extend({
      options: { position: 'topleft' },
      onAdd() {
        const btn = L.DomUtil.create('button', 'leaflet-bar map-fit-btn')
        btn.type = 'button'
        btn.title = '반경 전체 보기'
        btn.setAttribute('aria-label', '반경 전체 보기')
        btn.innerHTML = '<span aria-hidden="true">⤢</span>'
        L.DomEvent.disableClickPropagation(btn)
        L.DomEvent.on(btn, 'click', () => fitAll())
        return btn
      },
    })
    new FitControl().addTo(map)

    layersRef.current.area = L.layerGroup().addTo(map)
    layersRef.current.shops = L.layerGroup().addTo(map)
    mapRef.current = map

    // 레이아웃이 바뀌면(창 크기 변경, 화면 회전 등) 크기가 안정된 뒤 다시 계산하고, 반경 원이 잘리면 다시 맞춘다
    let resizeTimer = null
    let lastSize = ''
    const ro = new ResizeObserver(([entry]) => {
      const size = `${Math.round(entry.contentRect.width)}x${Math.round(entry.contentRect.height)}`
      if (size === lastSize) return
      lastSize = size
      clearTimeout(resizeTimer)
      resizeTimer = setTimeout(() => {
        map.invalidateSize({ pan: false })
        if (areaRef.current && needsRefit()) fitAll()
      }, 200)
    })
    ro.observe(elRef.current)
    return () => {
      ro.disconnect()
      clearTimeout(resizeTimer)
      clearTimeout(hintTimer)
      container.removeEventListener('wheel', onWheel)
      map.remove()
      mapRef.current = null
      layersRef.current = { area: null, shops: null, markers: new Map(), circle: null }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 검색 중심 + 반경 원
  useEffect(() => {
    const { area } = layersRef.current
    if (!mapRef.current || !area) return
    area.clearLayers()
    layersRef.current.circle = null
    areaRef.current = center ? { lat: center.lat, lng: center.lng, radius } : null
    if (!center) return
    const accent = cssVar('--accent', '#2a78d6')
    layersRef.current.circle = L.circle([center.lat, center.lng], {
      radius,
      color: accent,
      weight: 2,
      fillColor: accent,
      fillOpacity: 0.07,
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
    fitAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center, radius])

  // 업소 마커: 결과가 바뀔 때마다 모두 다시 그리고 범위를 맞춘다
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
        .bindTooltip(
          `${s.bssh_nm} · ${s.distance_m < 1000 ? `${s.distance_m}m` : `${(s.distance_m / 1000).toFixed(1)}km`}`,
          { direction: 'top', offset: [0, -6] },
        )
        .on('click', (e) => {
          L.DomEvent.stopPropagation(e) // 지도 클릭(위치 변경)으로 번지지 않게
          handlers.current.onSelect?.(s.id)
        })
        .addTo(shops)
      markers.set(s.id, m)
    }
    if (areaRef.current) fitAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items])

  // 선택된 업소 강조 (축소돼 있으면 반경 전체가 보이도록 먼저 맞춤)
  useEffect(() => {
    const map = mapRef.current
    const { markers } = layersRef.current
    if (!map) return
    const fill = cssVar('--series', '#2a78d6')
    const hi = cssVar('--highlight', '#eb6834')
    let selected = null
    markers.forEach((m, id) => {
      const on = id === selectedId
      m.setStyle({ radius: on ? 11 : 6, fillColor: on ? hi : fill, weight: on ? 3 : 2 })
      if (on) selected = m
      else m.closeTooltip()
    })
    if (!selected) return
    if (needsRefit()) fitAll()
    else if (!map.getBounds().contains(selected.getLatLng())) map.panTo(selected.getLatLng())
    selected.bringToFront()
    selected.openTooltip()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, items])

  return (
    <div
      ref={elRef}
      className="map"
      role="application"
      aria-label="주변 업소 지도. 지도를 클릭하면 그 위치로 검색합니다."
    />
  )
}
