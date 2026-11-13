import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchNearby, fetchStats, geocodeAddress } from '../api.js'
import { todayYmd } from '../dates.js'
import ExpiryBadge from '../components/ExpiryBadge.jsx'
import NearbyMap from '../components/NearbyMap.jsx'

const RADII = [
  { value: 500, label: '500m' },
  { value: 1000, label: '1km' },
  { value: 3000, label: '3km' },
]
const FALLBACK_HINT = '지도를 클릭하거나 주소를 입력하세요.'

const fmtDistance = (m) => (m < 1000 ? `${m}m` : `${(m / 1000).toFixed(m < 10000 ? 1 : 0)}km`)

export default function NearbyPage() {
  const [params, setParams] = useSearchParams()
  const lat = Number(params.get('lat'))
  const lng = Number(params.get('lng'))
  const radius = RADII.some((r) => r.value === Number(params.get('r'))) ? Number(params.get('r')) : 1000
  const type = params.get('type') || ''
  const expiring = params.get('exp') === '1'
  const hasCenter = Number.isFinite(lat) && Number.isFinite(lng) && lat !== 0 && lng !== 0

  const [label, setLabel] = useState(params.get('label') || '')
  const [query, setQuery] = useState('')
  const [alts, setAlts] = useState([])
  const [types, setTypes] = useState([])
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searching, setSearching] = useState(false)
  const [locating, setLocating] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const listRef = useRef(null)

  const center = useMemo(
    () => (hasCenter ? { lat, lng, label: label || `${lat.toFixed(5)}, ${lng.toFixed(5)}` } : null),
    [hasCenter, lat, lng, label],
  )

  const update = useCallback(
    (next) => {
      const cur = Object.fromEntries(params.entries())
      const merged = { ...cur, ...next }
      setParams(Object.fromEntries(Object.entries(merged).filter(([, v]) => v !== '' && v != null)), {
        replace: true,
      })
    },
    [params, setParams],
  )

  const moveTo = useCallback(
    (p, newLabel = '', keepAlts = false) => {
      if (!keepAlts) setAlts([])
      setLabel(newLabel)
      setSelectedId(null)
      setNotice('')
      update({ lat: p.lat.toFixed(6), lng: p.lng.toFixed(6), label: newLabel })
    },
    [update],
  )

  useEffect(() => {
    fetchStats({ active_only: true })
      .then((s) => setTypes(s.by_type.map((t) => t.key)))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!hasCenter) return
    let cancelled = false
    setLoading(true)
    setError('')
    fetchNearby({ lat, lng, radius, type, expiring, active_only: true, limit: 300 })
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [hasCenter, lat, lng, radius, type, expiring])

  // 마커에서 고른 업소가 목록에서 보이도록 스크롤
  useEffect(() => {
    if (selectedId == null || !listRef.current) return
    listRef.current
      .querySelector(`[data-id="${selectedId}"]`)
      ?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [selectedId])

  async function onSearch(e) {
    e.preventDefault()
    const q = query.trim()
    if (q.length < 2) {
      setNotice('주소나 동네 이름을 2글자 이상 입력하세요.')
      return
    }
    setSearching(true)
    setNotice('')
    try {
      const r = await geocodeAddress(q)
      moveTo(r, r.label)
      setAlts(r.alternatives || [])
    } catch (err) {
      setNotice(err.message)
    } finally {
      setSearching(false)
    }
  }

  function onMyLocation() {
    if (!window.isSecureContext || !navigator.geolocation) {
      setNotice(`이 주소(https 아님)에서는 내 위치를 쓸 수 없습니다. ${FALLBACK_HINT}`)
      return
    }
    setLocating(true)
    setNotice('')
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false)
        moveTo({ lat: pos.coords.latitude, lng: pos.coords.longitude }, '내 위치')
      },
      (err) => {
        setLocating(false)
        const why = err.code === err.PERMISSION_DENIED ? '위치 권한이 거부되었습니다.' : '위치를 가져오지 못했습니다.'
        setNotice(`${why} ${FALLBACK_HINT}`)
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 },
    )
  }

  const items = data?.items || []
  const summary = data?.summary
  const today = data?.today || todayYmd()
  const radiusLabel = RADII.find((r) => r.value === radius)?.label

  return (
    <section className="nearby">
      <div className="hero">
        <h1>내 주변 식품안심업소</h1>
        <p>지도를 클릭하거나 주소·동네 이름을 입력하면 반경 안의 식품안심업소와 업종별 현황을 보여드려요.</p>
      </div>

      <form className="search" onSubmit={onSearch} role="search">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="주소 또는 동네 이름 (예: 동성로, 대구 중구 국채보상로 600)"
          aria-label="주소 또는 동네 이름"
        />
        <button type="submit" className="btn-primary" disabled={searching}>
          {searching ? '찾는 중…' : '찾기'}
        </button>
      </form>

      <div className="filters">
        <button type="button" className="btn-ghost btn-locate" onClick={onMyLocation} disabled={locating}>
          <span aria-hidden="true">◎</span> {locating ? '위치 확인 중…' : '내 위치'}
        </button>
        <div className="segmented" role="radiogroup" aria-label="반경">
          {RADII.map((r) => (
            <button
              key={r.value}
              type="button"
              role="radio"
              aria-checked={radius === r.value}
              className={radius === r.value ? 'on' : ''}
              onClick={() => update({ r: String(r.value) })}
            >
              {r.label}
            </button>
          ))}
        </div>
        <select value={type} onChange={(e) => update({ type: e.target.value })} aria-label="업종">
          <option value="">전체 업종</option>
          {types.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <label className="toggle">
          <input type="checkbox" checked={expiring} onChange={(e) => update({ exp: e.target.checked ? '1' : '' })} />
          만료 3개월 이내
        </label>
      </div>

      {alts.length > 0 && (
        <div className="alts">
          <span className="muted small">
            검색 위치: <strong>{label}</strong> · 다른 곳을 찾으셨나요?
          </span>
          {alts.map((a) => (
            <button
              key={`${a.lat},${a.lng}`}
              type="button"
              className="chip-btn"
              onClick={() => {
                const prev = { lat, lng, label }
                setAlts((list) => [prev, ...list.filter((x) => x !== a)])
                moveTo(a, a.label, true)
              }}
            >
              {a.label}
            </button>
          ))}
          <span className="muted small">지역명을 함께 입력하면 더 정확해요 (예: 대구 동성로)</span>
        </div>
      )}

      {notice && <p className="notice">{notice}</p>}
      {error && <p className="notice notice-error">주변 업소를 불러오지 못했습니다: {error}</p>}

      {summary && (
        <div className="nb-summary" aria-live="polite">
          <div className="nb-sum-main">
            <span className="tile-label">
              {center?.label} 반경 {radiusLabel}
            </span>
            <span className="tile-value">{summary.total.toLocaleString()}곳</span>
            <span className="tile-sub">
              <span className="status-dot warning" aria-hidden="true" />
              만료 임박 {summary.expiring.toLocaleString()}곳
            </span>
          </div>
          {summary.by_type.map((t) => (
            <button
              key={t.key}
              type="button"
              className={`nb-sum-type${type === t.key ? ' on' : ''}`}
              onClick={() => update({ type: type === t.key ? '' : t.key })}
              aria-pressed={type === t.key}
              title={type === t.key ? '업종 필터 해제' : `${t.key}만 보기`}
            >
              <span className="rt-type-name">{t.key}</span>
              <span className="rt-type-count">{t.count.toLocaleString()}곳</span>
              <span className="rt-type-share">
                반경 내 {t.count / summary.total < 0.01 ? '1% 미만' : `${Math.round((t.count / summary.total) * 100)}%`}
              </span>
            </button>
          ))}
          {summary.total === 0 && <p className="muted small nb-sum-empty">이 반경 안에는 식품안심업소가 없습니다.</p>}
        </div>
      )}

      <div className="nb-layout">
        <div className="nb-map-wrap">
          <NearbyMap
            center={center}
            radius={radius}
            items={items}
            selectedId={selectedId}
            onPick={(p) => moveTo(p)}
            onSelect={setSelectedId}
          />
          {!center && <div className="map-hint">{FALLBACK_HINT}</div>}
          <p className="map-credit">
            지도 데이터 ©{' '}
            <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
              OpenStreetMap
            </a>{' '}
            기여자 · 위치 검색: 카카오 로컬 API
          </p>
        </div>

        <div className="nb-list" ref={listRef}>
          <div className="nb-list-head">
            {center ? (
              <>
                <strong>{data ? data.total.toLocaleString() : '…'}</strong>곳
                {type && ` · ${type}`}
                {expiring && ' · 만료 임박'}
                <span className="muted"> · 가까운 순</span>
              </>
            ) : (
              <span className="muted">위치를 고르면 가까운 업소가 여기에 표시됩니다.</span>
            )}
          </div>
          {data && data.total > items.length && (
            <p className="muted small nb-cap">가까운 {items.length}곳만 표시합니다. 반경을 줄이거나 업종을 골라 보세요.</p>
          )}
          <ul className={loading ? 'is-loading' : ''}>
            {items.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  data-id={s.id}
                  className={`nb-item${selectedId === s.id ? ' on' : ''}`}
                  onClick={() => setSelectedId(s.id)}
                  aria-pressed={selectedId === s.id}
                >
                  <span className="nb-dist">{fmtDistance(s.distance_m)}</span>
                  <span className="nb-body">
                    <span className="nb-name">{s.bssh_nm}</span>
                    <span className="nb-addr">{s.addr}</span>
                    <span className="nb-meta">
                      <span className="chip">{s.induty_nm}</span>
                      <ExpiryBadge asgnTo={s.asgn_to} today={today} windowDays={data.expiry_window_days} />
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {data && center && items.length === 0 && !loading && (
            <p className="empty">조건에 맞는 업소가 없습니다.</p>
          )}
        </div>
      </div>

      {data && data.geocoded_ratio < 0.99 && (
        <p className="muted small">
          현재 위치 정보(좌표)가 확인된 업소는 전체의 {(data.geocoded_ratio * 100).toFixed(1)}%입니다. 좌표가 없는
          업소는 지도와 목록에 나오지 않습니다.
        </p>
      )}
    </section>
  )
}
