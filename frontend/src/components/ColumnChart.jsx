import { useState } from 'react'

/**
 * 월별 세로 막대 (단일 계열). items: [{ key: 'YYYYMM', count }]
 * 이번 달은 집계 중이라 옅게 표시하고, 최댓값 막대에만 값 라벨을 단다.
 */
export default function ColumnChart({ items, currentMonth }) {
  const [hover, setHover] = useState(null)
  if (!items.length) return <p className="muted small">데이터가 없습니다.</p>
  const max = Math.max(1, ...items.map((i) => i.count))
  const maxKey = items.reduce((a, b) => (b.count > a.count ? b : a)).key
  const ticks = [max, Math.round(max / 2), 0]

  return (
    <div className="colchart">
      <div className="col-axis" aria-hidden="true">
        {ticks.map((t) => (
          <span key={t}>{t.toLocaleString()}</span>
        ))}
      </div>
      <div className="col-plot">
        <div className="col-grid" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <ol className="col-bars">
          {items.map((it, idx) => {
            const y = it.key.slice(0, 4)
            const m = Number(it.key.slice(4, 6))
            const partial = it.key === currentMonth
            const showYear = idx === 0 || m === 1
            return (
              <li
                key={it.key}
                className={`col${hover === it.key ? ' hover' : ''}`}
                tabIndex={0}
                aria-label={`${y}년 ${m}월 ${it.count.toLocaleString()}곳${partial ? ' (집계 중)' : ''}`}
                onMouseEnter={() => setHover(it.key)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(it.key)}
                onBlur={() => setHover(null)}
              >
                <span className="col-hit">
                  <span
                    className={`col-fill${partial ? ' partial' : ''}`}
                    style={{ height: `${(it.count / max) * 100}%` }}
                  >
                    {it.key === maxKey && <span className="col-label">{it.count.toLocaleString()}</span>}
                  </span>
                </span>
                <span className="col-x">
                  {m}
                  {showYear && <span className="col-year">{y}</span>}
                </span>
                {hover === it.key && (
                  <span className="bar-tip col-tip" role="tooltip">
                    <strong>
                      {y}년 {m}월
                    </strong>
                    <span>
                      {it.count.toLocaleString()}곳 지정{partial ? ' · 집계 중' : ''}
                    </span>
                  </span>
                )}
              </li>
            )
          })}
        </ol>
      </div>
    </div>
  )
}
