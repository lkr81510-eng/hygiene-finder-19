// YYYYMMDD 문자열 유틸

export function parseYmd(v) {
  const s = String(v || '').replace(/\D/g, '')
  if (s.length < 8) return null
  return new Date(Number(s.slice(0, 4)), Number(s.slice(4, 6)) - 1, Number(s.slice(6, 8)))
}

export function fmtYmd(v) {
  const s = String(v || '').replace(/\D/g, '')
  return s.length >= 8 ? `${s.slice(0, 4)}.${s.slice(4, 6)}.${s.slice(6, 8)}` : v || ''
}

/** 오늘(today: YYYYMMDD)부터 지정종료일까지 남은 일수. 지났으면 음수 */
export function daysUntil(ymd, today) {
  const a = parseYmd(today)
  const b = parseYmd(ymd)
  if (!a || !b) return null
  return Math.round((b - a) / 86400000)
}

export function todayYmd() {
  const d = new Date()
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
}
