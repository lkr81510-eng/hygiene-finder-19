import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchRegion } from '../api.js'

const pct = (v) => `${(v * 100).toFixed(1)}%`

/** 지역 × 업종: 시도를 고르면 업종별 식품안심업소 수와 시군구별 분포를 보여준다. */
export default function RegionTypeTable({ regions, region, onRegionChange, activeOnly }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [sort, setSort] = useState({ col: 'total', dir: -1 })

  useEffect(() => {
    if (!region) return
    let cancelled = false
    setError('')
    fetchRegion({ region, active_only: activeOnly })
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e.message))
    return () => {
      cancelled = true
    }
  }, [region, activeOnly])

  const rows = useMemo(() => {
    if (!data) return []
    const val = (r) => (sort.col === 'key' ? r.key : sort.col === 'total' ? r.total : r.types[sort.col] || 0)
    return [...data.sigungu].sort((a, b) => {
      const va = val(a)
      const vb = val(b)
      if (typeof va === 'string') return va.localeCompare(vb, 'ko') * sort.dir
      return (va - vb) * sort.dir || a.key.localeCompare(b.key, 'ko')
    })
  }, [data, sort])

  const cellMax = useMemo(() => {
    if (!data) return 1
    return Math.max(1, ...data.sigungu.flatMap((r) => Object.values(r.types)))
  }, [data])

  function sortBy(col) {
    setSort((s) => (s.col === col ? { col, dir: -s.dir } : { col, dir: col === 'key' ? 1 : -1 }))
  }

  function sortTh(col, children, className) {
    const active = sort.col === col
    return (
      <th key={col} className={className} aria-sort={active ? (sort.dir > 0 ? 'ascending' : 'descending') : 'none'}>
        <button type="button" className="th-sort" onClick={() => sortBy(col)}>
          {children}
          <span className="sort-mark" aria-hidden="true">
            {active ? (sort.dir > 0 ? '▲' : '▼') : ''}
          </span>
        </button>
      </th>
    )
  }

  const searchLink = (params) =>
    '/?' + new URLSearchParams(Object.fromEntries(Object.entries(params).filter(([, v]) => v))).toString()

  return (
    <div className="panel panel-wide rt">
      <div className="rt-head">
        <div>
          <h2>지역 × 업종 경쟁 현황</h2>
          <p className="muted small">
            창업 예정 지역을 고르면 업종별 식품안심업소 수와 시군구별 분포를 볼 수 있습니다.
          </p>
        </div>
        <select value={region} onChange={(e) => onRegionChange(e.target.value)} aria-label="시도 선택">
          {regions.map((r) => (
            <option key={r.key} value={r.key}>
              {r.key}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="notice notice-error">{error}</p>}
      {data && (
        <>
          <div className="rt-summary">
            {data.by_type.map((t) => {
              const diff = t.share - t.national_share
              return (
                <Link key={t.key} className="rt-type" to={searchLink({ region, type: t.key })}>
                  <span className="rt-type-name">{t.key}</span>
                  <span className="rt-type-count">{t.count.toLocaleString()}곳</span>
                  <span className="rt-type-share">
                    지역 내 {pct(t.share)}
                    <span className={`delta ${diff >= 0 ? 'up' : 'down'}`}>
                      {' '}
                      (전국 {pct(t.national_share)}
                      {Math.abs(diff) >= 0.005 && <>, {diff > 0 ? '▲' : '▼'}{(Math.abs(diff) * 100).toFixed(1)}%p</>})
                    </span>
                  </span>
                </Link>
              )
            })}
          </div>

          <div className="table-scroll">
            <table className="matrix">
              <caption className="sr-only">
                {data.region} 시군구별 업종별 식품안심업소 수
              </caption>
              <thead>
                <tr>
                  {sortTh('key', '시군구', 'sticky-col')}
                  {data.types.map((t) => sortTh(t, t))}
                  {sortTh('total', '합계')}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.key}>
                    <th scope="row" className="sticky-col">
                      {r.key}
                    </th>
                    {data.types.map((t) => {
                      const v = r.types[t] || 0
                      return (
                        <td key={t} style={{ '--v': v / cellMax }} className={v ? 'heat' : 'zero'}>
                          {v ? v.toLocaleString() : '–'}
                        </td>
                      )
                    })}
                    <td className="total">{r.total.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <th scope="row" className="sticky-col">
                    {data.region} 전체
                  </th>
                  {data.types.map((t) => (
                    <td key={t}>{(data.by_type.find((x) => x.key === t)?.count || 0).toLocaleString()}</td>
                  ))}
                  <td className="total">{data.total.toLocaleString()}</td>
                </tr>
              </tfoot>
            </table>
          </div>
          <p className="muted small">
            셀 색이 진할수록 업소가 많습니다. 열 제목을 누르면 정렬되고, 업종 카드를 누르면 해당 업소 목록으로 이동합니다.
          </p>
        </>
      )}
    </div>
  )
}
