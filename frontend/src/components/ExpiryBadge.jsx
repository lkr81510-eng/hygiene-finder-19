import { daysUntil, fmtYmd } from '../dates.js'

/** 지정 상태 배지: 유효 / 만료 임박(windowDays 이내) / 만료. 색 + 아이콘 + 글자로 표시 */
export default function ExpiryBadge({ asgnTo, today, windowDays = 90 }) {
  const d = daysUntil(asgnTo, today)
  if (d === null) return null
  if (d < 0)
    return (
      <span className="badge status-critical" title={`지정종료일 ${fmtYmd(asgnTo)}`}>
        <span className="badge-icon" aria-hidden="true">✕</span>
        지정 만료
      </span>
    )
  if (d <= windowDays)
    return (
      <span className="badge status-warning" title={`지정종료일 ${fmtYmd(asgnTo)}`}>
        <span className="badge-icon" aria-hidden="true">!</span>
        만료 {d === 0 ? '오늘' : `D-${d}`}
      </span>
    )
  return (
    <span className="badge status-good" title={`지정종료일 ${fmtYmd(asgnTo)}`}>
      <span className="badge-icon" aria-hidden="true">✓</span>
      지정 유효
    </span>
  )
}
