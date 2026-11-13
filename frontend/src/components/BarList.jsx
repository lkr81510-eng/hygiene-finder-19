import { useState } from 'react'

/**
 * 가로 막대 차트 (단일 계열). 값 라벨을 항상 표시하고, 막대에 마우스를 올리면 툴팁을 보여준다.
 * onSelect 가 있으면 행을 눌러 선택할 수 있다.
 */
export default function BarList({ items, total, labelFor = (i) => i.key, limit, onSelect }) {
  const [hover, setHover] = useState(null)
  let rows = items
  if (limit && items.length > limit) {
    const rest = items.slice(limit)
    rows = [
      ...items.slice(0, limit),
      { key: `기타 (${rest.length}개)`, count: rest.reduce((s, r) => s + r.count, 0), other: true },
    ]
  }
  const max = Math.max(1, ...rows.map((r) => r.count))

  return (
    <ul className="barlist">
      {rows.map((r) => {
        const pct = total ? (r.count / total) * 100 : 0
        const selectable = onSelect && !r.other
        return (
          <li
            key={r.key}
            className={`bar-row${hover === r.key ? ' hover' : ''}${selectable ? ' selectable' : ''}`}
            onMouseEnter={() => setHover(r.key)}
            onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(r.key)}
            onBlur={() => setHover(null)}
            onClick={selectable ? () => onSelect(r) : undefined}
            onKeyDown={
              selectable
                ? (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      onSelect(r)
                    }
                  }
                : undefined
            }
            role={selectable ? 'button' : undefined}
            tabIndex={0}
          >
            <span className="bar-label" title={labelFor(r)}>
              {labelFor(r)}
            </span>
            <span className="bar-track">
              <span
                className={`bar-fill ${r.other ? 'bar-other' : 'bar-series'}`}
                style={{ width: `${(r.count / max) * 100}%` }}
              />
              {hover === r.key && (
                <span className="bar-tip" role="tooltip">
                  <strong>{labelFor(r)}</strong>
                  <span>
                    {r.count.toLocaleString()}곳 · {pct.toFixed(1)}%
                  </span>
                </span>
              )}
            </span>
            <span className="bar-value">{r.count.toLocaleString()}</span>
          </li>
        )
      })}
    </ul>
  )
}
