import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchShops, fetchStats } from '../api.js'
import { todayYmd } from '../dates.js'
import Pagination from '../components/Pagination.jsx'
import ShopCard from '../components/ShopCard.jsx'

const PAGE_SIZE = 24

export default function SearchPage() {
  const [params, setParams] = useSearchParams()
  const name = params.get('name') || ''
  const region = params.get('region') || ''
  const type = params.get('type') || ''
  const expiring = params.get('exp') === '1'
  const activeOnly = params.get('all') !== '1'
  const page = Math.max(1, Number(params.get('page')) || 1)

  const [draft, setDraft] = useState(name)
  const [options, setOptions] = useState({ by_region: [], by_type: [], sync: null, expiry_window_days: 90 })
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => setDraft(name), [name])

  useEffect(() => {
    fetchStats({ active_only: true })
      .then(setOptions)
      .catch(() => {})
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    fetchShops({ name, region, type, expiring, active_only: activeOnly, page, size: PAGE_SIZE })
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [name, region, type, expiring, activeOnly, page])

  function update(next) {
    const merged = { name, region, type, exp: expiring ? '1' : '', all: activeOnly ? '' : '1', page: '', ...next }
    const clean = Object.fromEntries(Object.entries(merged).filter(([, v]) => v !== '' && v != null))
    setParams(clean)
  }

  function onSubmit(e) {
    e.preventDefault()
    update({ name: draft.trim() })
  }

  function goPage(p) {
    update({ page: p > 1 ? String(p) : '' })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const hasFilter = name || region || type || expiring || !activeOnly
  const sync = options.sync
  const windowDays = data?.expiry_window_days ?? options.expiry_window_days
  const today = data?.today || todayYmd()

  return (
    <section>
      <div className="hero">
        <h1>우리 동네 식품안심업소 찾기</h1>
        <p>식약처가 위생 수준을 평가해 지정한 음식점을 업소명·지역·업종으로 검색해 보세요.</p>
      </div>

      <form className="search" onSubmit={onSubmit} role="search">
        <input
          type="search"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="업소명으로 검색 (예: 김밥, 카페)"
          aria-label="업소명 검색"
        />
        <button type="submit" className="btn-primary">
          검색
        </button>
      </form>

      <div className="filters">
        <select value={region} onChange={(e) => update({ region: e.target.value })} aria-label="지역">
          <option value="">전체 지역</option>
          {options.by_region.map((r) => (
            <option key={r.key} value={r.key}>
              {r.key}
            </option>
          ))}
        </select>
        <select value={type} onChange={(e) => update({ type: e.target.value })} aria-label="업종">
          <option value="">전체 업종</option>
          {options.by_type.map((t) => (
            <option key={t.key} value={t.key}>
              {t.key}
            </option>
          ))}
        </select>
        <label className="toggle">
          <input type="checkbox" checked={expiring} onChange={(e) => update({ exp: e.target.checked ? '1' : '' })} />
          만료 3개월 이내
        </label>
        <label className="toggle">
          <input type="checkbox" checked={activeOnly} onChange={(e) => update({ all: e.target.checked ? '' : '1' })} />
          영업 중인 업소만
        </label>
        {hasFilter && (
          <button
            type="button"
            className="btn-ghost"
            onClick={() => {
              setDraft('')
              setParams({})
            }}
          >
            초기화
          </button>
        )}
      </div>

      <div className="result-bar">
        <span>
          {data ? (
            <>
              검색 결과 <strong>{data.total.toLocaleString()}</strong>곳
              {expiring && <span className="muted"> · 지정종료일이 가까운 순</span>}
            </>
          ) : (
            ' '
          )}
        </span>
        {sync?.finished_at && sync.status === 'ok' && (
          <span className="muted">데이터 갱신 {new Date(sync.finished_at).toLocaleString('ko-KR')}</span>
        )}
      </div>

      {error && <p className="notice notice-error">데이터를 불러오지 못했습니다: {error}</p>}

      {sync && sync.status !== 'ok' && data?.total === 0 && !hasFilter && (
        <p className="notice">
          {sync.status === 'running'
            ? '데이터를 동기화하는 중입니다. 잠시 후 새로고침해 주세요.'
            : `아직 데이터가 없습니다. ${sync.message || '백엔드 동기화 상태를 확인하세요.'}`}
        </p>
      )}

      {loading && !data ? (
        <div className="grid">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="card skeleton" />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <div className={`grid${loading ? ' is-loading' : ''}`}>
          {data.items.map((s) => (
            <ShopCard key={s.id} shop={s} today={today} windowDays={windowDays} />
          ))}
        </div>
      ) : (
        data && !error && <p className="empty">조건에 맞는 업소가 없습니다.</p>
      )}

      {data && <Pagination page={data.page} pages={data.pages} onChange={goPage} />}
    </section>
  )
}
